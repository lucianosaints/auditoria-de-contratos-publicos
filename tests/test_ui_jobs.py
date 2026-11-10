import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.ui_jobs import execute_action, job_lock, run_job


class UIJobsTests(unittest.TestCase):
    def test_financial_action_uses_selected_run_without_llm_or_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'data/reports/selected'; folder.mkdir(parents=True)
            (folder / 'contratos.json').write_text('[{}]', encoding='utf-8')
            (folder / 'parecer.json').write_text(json.dumps({'linhas_analisadas': [1],
                'suspeitos': [], 'relatorio_markdown': 'Parecer'}), encoding='utf-8')
            with patch('src.ui_jobs.ROOT', root), patch('src.main.create_audit_llm') as llm, \
                    patch('src.database.init_db') as db, patch('src.financial.collect_financial',
                    return_value={'processados': 1, 'consultas_fornecedores': [], 'detalhes_consultados': 0, 'consultas': []}) as collect:
                code, result = execute_action('consultar_financeiro', 'selected')
                self.assertEqual(code, 0)
                self.assertEqual(result['financeiro']['contratos'], 1)
                self.assertEqual(collect.call_args.args[0], folder)
                llm.assert_not_called(); db.assert_not_called()

    def test_indicator_action_keeps_selected_execution_and_avoids_llm_and_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'data/reports/selected'; folder.mkdir(parents=True)
            (folder / 'contratos.json').write_text('[{}]', encoding='utf-8')
            (folder / 'parecer.json').write_text(json.dumps({'linhas_analisadas': [1],
                'suspeitos': [], 'relatorio_markdown': 'Parecer'}), encoding='utf-8')
            with patch('src.ui_jobs.ROOT', root), patch('src.main.create_audit_llm') as llm, \
                    patch('src.database.init_db') as db:
                code, result = execute_action('gerar_indicadores', 'selected')
                self.assertEqual(code, 0)
                self.assertEqual(result['indicadores']['linhas_coletadas'], 1)
                self.assertTrue((folder / 'indicadores.json').is_file())
                llm.assert_not_called(); db.assert_not_called()

    def test_pncp_action_uses_selected_run_without_llm_or_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'data/reports/selected'; folder.mkdir(parents=True)
            (folder / 'contratos.json').write_text('[{}]', encoding='utf-8')
            (folder / 'parecer.json').write_text(json.dumps({'linhas_analisadas': [1],
                'suspeitos': [], 'relatorio_markdown': 'Parecer'}), encoding='utf-8')
            with patch('src.ui_jobs.ROOT', root), patch('src.main.create_audit_llm') as llm, \
                    patch('src.database.init_db') as db, patch('src.pncp.collect_pncp',
                    return_value={'status': 'concluida', 'consultas': []}) as collect:
                code, result = execute_action('consultar_pncp', 'selected')
                self.assertEqual(code, 0)
                self.assertEqual(result['pncp']['confirmados'], 0)
                self.assertEqual(collect.call_args.args[0], folder)
                llm.assert_not_called(); db.assert_not_called()

    def test_estimate_uses_same_gemini_model_identity_as_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'data/reports/selected'; folder.mkdir(parents=True)
            (folder / 'contratos.json').write_text('[{}]', encoding='utf-8')
            (folder / 'parecer.json').write_text(json.dumps({'linhas_analisadas': [1],
                'suspeitos': [], 'relatorio_markdown': 'Original'}), encoding='utf-8')
            summary = {'contratos_reaproveitados': 13, 'contratos_pendentes': 81, 'chamadas_maximas_de_etapas': 72}
            with patch('src.ui_jobs.ROOT', root), patch.dict('os.environ', {'GEMINI_MODEL': 'gemini/gemini-3.5-flash-lite'}), \
                    patch('src.agent_review.plan_saved_review', return_value=summary) as plan:
                self.assertEqual(execute_action('planejar_revisao', 'selected'), (0, summary))
                self.assertEqual(plan.call_args.kwargs['model'], 'gemini-3.5-flash-lite')

    def test_document_actions_plan_and_collect_without_llm_or_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'data/reports/selected'
            folder.mkdir(parents=True)
            (folder / 'contratos.json').write_text('[{"Objeto":"Serviço demonstrativo"}]', encoding='utf-8')
            (folder / 'parecer.json').write_text(json.dumps({'linhas_analisadas': [1],
                'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Conferir'}], 'relatorio_markdown': 'Parecer'}), encoding='utf-8')
            with patch('src.ui_jobs.ROOT', root), patch('src.main.create_audit_llm') as llm, patch('src.database.init_db') as db:
                status, plan = execute_action('planejar_documentos', 'selected')
                self.assertEqual(status, 0); self.assertEqual(plan['contratos_sem_links'], 1)
                self.assertFalse((folder / 'documentos.json').exists())
                with patch('src.documents.collect_documents', return_value={'status': 'com_pendencias', 'documentos_processados': 0}) as collect:
                    self.assertEqual(execute_action('coletar_documentos', 'selected')[1]['documentos_processados'], 0)
                    self.assertEqual(collect.call_args.args[0], folder)
                llm.assert_not_called(); db.assert_not_called()

    def job(self, directory, action='revisar_achados'):
        folder = Path(directory)
        job = {'id': 'job1', 'action': action, 'run_id': 'selected', 'status': 'iniciando'}
        (folder / 'job1.json').write_text(json.dumps(job), encoding='utf-8')
        return folder

    def test_success_records_terminal_status_and_preserves_action_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.job(directory)
            operation = Mock(return_value=(0, {'contratos_revisados': 1}))
            self.assertEqual(run_job('job1', jobs_root=root, operation=operation, monitor_cancel=False), 0)
            operation.assert_called_once_with('revisar_achados', 'selected')
            saved = json.loads((root / 'job1.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['status'], 'concluido')
            self.assertIn('finished_at', saved)

    def test_cancel_before_start_does_not_call_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.job(directory)
            (root / 'job1.cancel').touch()
            operation = Mock()
            self.assertEqual(run_job('job1', jobs_root=root, operation=operation, monitor_cancel=False), 130)
            operation.assert_not_called()
            self.assertEqual(json.loads((root / 'job1.json').read_text(encoding='utf-8'))['status'], 'interrompido')

    def test_failure_is_terminal_and_does_not_expose_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.job(directory)
            operation = Mock(side_effect=RuntimeError('https://example.org/?key=secret'))
            self.assertEqual(run_job('job1', jobs_root=root, operation=operation, monitor_cancel=False), 1)
            saved = json.loads((root / 'job1.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['status'], 'falhou')
            self.assertNotIn('key=secret', saved['mensagem'])

    def test_cancel_during_operation_preserves_interrupt_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.job(directory)
            def operation(*args):
                raise KeyboardInterrupt
            self.assertEqual(run_job('job1', jobs_root=root, operation=operation, monitor_cancel=False), 130)

    def test_shared_runner_lock_blocks_another_action_and_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.job(directory)
            operation = Mock()
            with job_lock(root):
                self.assertEqual(run_job('job1', jobs_root=root, operation=operation, monitor_cancel=False), 1)
            operation.assert_not_called()
            with job_lock(root):
                pass

    def test_unknown_job_action_and_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.job(directory, 'execute_shell')
            with self.assertRaises(ValueError):
                run_job('job1', jobs_root=root, operation=Mock())
            with self.assertRaises(ValueError):
                run_job('../outside', jobs_root=root, operation=Mock())

    def test_new_audit_uses_reserved_id_instead_of_resume(self):
        with patch('src.main.main', return_value=0) as main:
            self.assertEqual(execute_action('nova_auditoria', '20261020T123456Z_abcdef12')[0], 0)
            main.assert_called_once_with([], run_id='20261020T123456Z_abcdef12')

    def test_planning_reads_saved_records_without_llm_or_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'data' / 'reports' / 'selected'
            folder.mkdir(parents=True)
            (folder / 'contratos.json').write_text('[{"Objeto":"Servicos de manutencao"}]', encoding='utf-8')
            (folder / 'parecer.json').write_text(json.dumps({'linhas_analisadas': [1],
                'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Conferir objeto'}], 'relatorio_markdown': 'Parecer'}), encoding='utf-8')
            with patch('src.ui_jobs.ROOT', root), patch('src.main.create_audit_llm') as llm, patch('src.database.init_db') as db:
                status, summary = execute_action('planejar_revisao', 'selected')
                self.assertEqual(status, 0)
                self.assertEqual(summary['chamadas_maximas_de_etapas'], 2)
                llm.assert_not_called(); db.assert_not_called()
            self.assertFalse((folder / 'revisao_agentes.json').exists())
