import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.audit_models import Achado, ParecerAuditoria
from src.batch_pipeline import (BatchSettings, audit_in_batches, batch_worker, encoded, find_pending,
                                global_coincidences, merge_audits, quota_delay, split_batches, validate_batch, execution_lock)
from src.batch_pipeline import AuditValidationError


def opinion(size, reason=None):
    return ParecerAuditoria(linhas_analisadas=list(range(1, size + 1)),
                           suspeitos=[Achado(linha=1, motivo_suspeita=reason)] if reason else [],
                           relatorio_markdown='Parecer local de teste')


class BatchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.settings = BatchSettings(max_records=2, max_bytes=1000, interval_seconds=0)
        self.records = [{'Processo': str(i), 'Objeto': 'Objeto ' + str(i)} for i in range(5)]
        self.llm = SimpleNamespace(model='test-only')

    def test_size_and_byte_bounds_preserve_all_source_records(self):
        records = [{'Objeto': 'á' * 180 + str(i)} for i in range(8)]
        batches = split_batches(records, self.settings)
        self.assertEqual([r for batch in batches for r in batch], records)
        self.assertTrue(all(len(batch) <= 2 and len(encoded(batch).encode('utf-8')) <= 1000 for batch in batches))
        with self.assertRaisesRegex(ValueError, 'Linha 1'):
            split_batches([{'Objeto': 'x' * 2000}], self.settings)

    def test_strict_indices_before_global_offset(self):
        invalid = opinion(2).model_copy(update={'suspeitos': [Achado(linha=3, motivo_suspeita='fora do lote')]})
        with self.assertRaises(ValueError):
            validate_batch(invalid, 2)
        merged = merge_audits(self.records, [(self.records[:2], opinion(2, 'A')), (self.records[2:], opinion(3, 'B'))], [])
        self.assertEqual([f.linha for f in merged.suspeitos], [1, 3])
        self.assertEqual(merged.linhas_analisadas, [1, 2, 3, 4, 5])

    def test_resume_does_not_repeat_completed_batches(self):
        calls = []
        def worker(llm, batch, folder):
            calls.append([r['Processo'] for r in batch])
            if len(calls) == 2:
                raise RuntimeError('falha temporaria')
            return opinion(len(batch), 'Conferir objeto')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(RuntimeError):
                audit_in_batches(self.llm, self.records, folder, self.settings, worker=worker)
            self.assertFalse((folder / 'parecer.json').exists())
            self.assertEqual(json.loads((folder / 'progresso.json').read_text())['lotes_concluidos'], 1)
            remaining = Mock(side_effect=lambda llm, batch, directory: opinion(len(batch), 'Conferir objeto'))
            result = audit_in_batches(self.llm, self.records, folder, self.settings, worker=remaining)
            self.assertEqual(remaining.call_count, 2)
            self.assertEqual([f.linha for f in result.suspeitos], [1, 3, 5])
            self.assertEqual(result.linhas_analisadas, [1, 2, 3, 4, 5])

    def test_changed_source_invalidates_cached_opinions(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            worker = Mock(side_effect=lambda llm, batch, directory: opinion(len(batch)))
            audit_in_batches(self.llm, self.records, folder, self.settings, worker=worker)
            changed = [dict(r) for r in self.records]
            changed[0]['Objeto'] = 'Alterado'
            worker.reset_mock()
            audit_in_batches(self.llm, changed, folder, self.settings, worker=worker)
            self.assertEqual(worker.call_count, 3)

    def test_429_waits_provider_delay_and_retries_only_current_batch(self):
        error = RuntimeError("429 RESOURCE_EXHAUSTED {'retryDelay': '95s'}")
        self.assertEqual(quota_delay(error), 97)
        worker = Mock(side_effect=[error, opinion(1)])
        wait = Mock()
        with tempfile.TemporaryDirectory() as directory:
            audit_in_batches(self.llm, self.records[:1], Path(directory), self.settings, worker=worker, wait=wait)
        self.assertEqual(worker.call_count, 2)
        self.assertIn(97, [call.args[0] for call in wait.call_args_list])

    def test_daily_quota_does_not_loop(self):
        worker = Mock(side_effect=RuntimeError('429 quota per day'))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'Cota diária'):
                audit_in_batches(self.llm, self.records[:1], Path(directory), self.settings, worker=worker, wait=Mock())
        self.assertEqual(worker.call_count, 1)

    def test_global_comparisons_include_nonadjacent_lines(self):
        records = [{'Processo': '12/2026'}, {'Processo': '33/2026'}, {'Processo': '12/2026'}]
        result = global_coincidences(records)
        self.assertEqual(result[0]['linhas'], [1, 3])

    def test_global_process_prefers_detail_over_combined_listing_column(self):
        records = [
            {'Nr [Nr Processo]': '390 [1400/2026]', 'Detalhe - Processo': '1400/2026'},
            {'Nr [Nr Processo]': '391 [1400/2026]', 'Detalhe - Processo': '1400/2026'},
        ]
        result = global_coincidences(records)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['linhas'], [1, 2])

    def test_global_process_falls_back_when_detail_is_empty(self):
        records = [{'Processo': '1400/2026', 'Detalhe - Processo': ''}, {'Processo': '1400/2026'}]
        self.assertEqual(global_coincidences(records)[0]['linhas'], [1, 2])

    def test_global_process_keeps_genuine_same_source_ambiguity_error(self):
        with self.assertRaisesRegex(ValueError, 'ambíguas'):
            global_coincidences([{'Processo': '1', 'Número do Processo': '2'}])

    def test_pending_selects_latest_without_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('001', '002', '003'):
                (root / name).mkdir()
                (root / name / 'contratos.json').write_text('[]')
            (root / '003' / 'arquivamento.json').write_text('{}')
            self.assertEqual(find_pending(root).name, '002')

    def test_execution_lock_prevents_two_resumes_and_is_released(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with execution_lock(folder):
                with self.assertRaisesRegex(RuntimeError, 'outra janela'):
                    with execution_lock(folder):
                        self.fail('A segunda execução não deve adquirir a trava.')
            with execution_lock(folder):
                pass

    def test_worker_only_sends_batch_context_and_disables_agent_retries(self):
        from crewai import LLM
        llm = LLM(model='openai/gpt-4o-mini', api_key='test-only')
        with tempfile.TemporaryDirectory() as directory:
            with patch('src.batch_pipeline.Crew') as crew:
                crew.return_value.kickoff.return_value.raw = opinion(1).model_dump_json()
                result = batch_worker(llm, self.records[:1], Path(directory))
                task = crew.call_args.kwargs['tasks'][0]
                self.assertEqual(json.loads(task.context[0].output.raw), self.records[:1])
                self.assertEqual(task.agent.max_retry_limit, 0)
                self.assertEqual(task.guardrail_max_retries, 0)
                self.assertEqual(result.linhas_analisadas, [1])

    def test_no_archive_if_a_batch_fails(self):
        from src.batch_pipeline import run_pipeline
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'contratos.json').write_text(json.dumps(self.records))
            with patch('src.batch_pipeline.audit_in_batches', side_effect=RuntimeError('erro')), patch('src.batch_pipeline.ArquivarContratosTool') as archive:
                with self.assertRaises(RuntimeError):
                    run_pipeline(self.llm, folder, self.settings, resume=True)
                archive.assert_not_called()

    def test_guardrail_failure_retries_only_batch_with_feedback_and_saves_raw(self):
        from crewai import LLM
        from crewai.tasks.task_output import TaskOutput
        llm = LLM(model='openai/gpt-4o-mini', api_key='test-only')
        records = [{'Valor do Contrato': 'R$ 312000.00'}]
        invalid = opinion(1, 'Valor zerado em serviço oneroso')
        valid = opinion(1, 'Quantitativos ausentes no resumo; solicitar documento')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch('src.batch_pipeline.Crew') as crew, patch('src.batch_pipeline.wait_seconds') as wait:
                responses = iter([invalid, valid])
                def kickoff():
                    task = crew.call_args.kwargs['tasks'][0]
                    audit = next(responses)
                    raw = audit.model_dump_json()
                    ok, result = task.guardrail(TaskOutput(description='teste', agent='teste', raw=raw))
                    if not ok:
                        raise Exception('Task failed guardrail validation. ' + result)
                    return SimpleNamespace(raw=result)
                crew.return_value.kickoff.side_effect = kickoff
                result = batch_worker(llm, records, folder)
                self.assertEqual(result.suspeitos[0].motivo_suspeita, valid.suspeitos[0].motivo_suspeita)
                self.assertEqual(crew.call_count, 2)
                wait.assert_called_once_with(65)
                final_task = crew.call_args.kwargs['tasks'][0]
                self.assertIn('REVISÃO OBRIGATÓRIA', final_task.description)
                self.assertIn('312000.00', final_task.description)
                rejected = list((folder / 'rejeicoes').glob('*.json'))
                self.assertEqual(len(rejected), 1)
                saved = json.loads(rejected[0].read_text(encoding='utf-8'))
                self.assertEqual(json.loads(saved['resposta_original'])['suspeitos'][0]['motivo_suspeita'], invalid.suspeitos[0].motivo_suspeita)

    def test_invalid_batch_stops_after_three_revisions_without_checkpoint(self):
        from crewai import LLM
        from crewai.tasks.task_output import TaskOutput
        llm = LLM(model='openai/gpt-4o-mini', api_key='test-only')
        records = [{'Valor': '312000.00'}]
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch('src.batch_pipeline.Crew') as crew, patch('src.batch_pipeline.wait_seconds') as wait:
                def kickoff():
                    task = crew.call_args.kwargs['tasks'][0]
                    ok, result = task.guardrail(TaskOutput(description='teste', agent='teste', raw=opinion(1, 'Valor zerado').model_dump_json()))
                    self.assertFalse(ok)
                    raise Exception('Task failed guardrail validation. ' + result)
                crew.return_value.kickoff.side_effect = kickoff
                with self.assertRaises(AuditValidationError):
                    batch_worker(llm, records, folder)
                self.assertEqual(crew.call_count, 3)
                self.assertEqual(wait.call_count, 2)
                self.assertEqual(len(list((folder / 'rejeicoes').glob('*.json'))), 3)
                self.assertFalse((folder / 'checkpoint.json').exists())


if __name__ == '__main__':
    unittest.main()
