import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.quality_evaluation import make_sample, evaluate, render_report, main


class QualityEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.records = [{'Objeto': str(i)} for i in range(4)]
        self.audit = {'suspeitos': [{'linha': 1}, {'linha': 2}]}
        self.sample = make_sample(self.records, self.audit, 20)

    def test_confusion_matrix_includes_missed_cases(self):
        for item, decision in zip(self.sample['itens'], [True, False, True, False]):
            item.update(exige_diligencia=decision, responsavel='Pessoa',
                        justificativa='Conferido no processo', fontes=['Processo, página 4'])
        result = evaluate(self.records, self.audit, self.sample)
        for key in ('verdadeiros_positivos', 'falsos_positivos', 'verdadeiros_negativos', 'falsos_negativos'):
            self.assertEqual(result[key], 1)
        self.assertEqual(result['precisao'], .5)
        self.assertEqual(result['sensibilidade'], .5)
        self.assertEqual(result['linhas_para_segunda_conferencia'], [2, 3])
        self.assertEqual([c['resultado'] for c in result['casos']], [
            'verdadeiros_positivos', 'falsos_positivos', 'falsos_negativos', 'verdadeiros_negativos'])
        self.assertEqual(result['casos'][1]['fontes'], ['Processo, página 4'])

    def test_pending_is_not_a_success(self):
        result = evaluate(self.records, self.audit, self.sample)
        self.assertEqual(result['pendentes'], 4)
        self.assertEqual(result['avaliados'], 0)
        self.assertIsNone(result['precisao'])
        self.assertIsNone(result['sensibilidade'])
        self.assertEqual(result['linhas_para_segunda_conferencia'], [])
        self.assertEqual(result['cobertura_por_grupo']['com_alerta'],
                         {'selecionados': 2, 'avaliados': 0, 'pendentes': 2})

    def test_partial_evaluation_exposes_unequal_coverage_without_mutation(self):
        self.sample['itens'][0].update(exige_diligencia=False, responsavel='Pessoa',
            justificativa='Conferido', fontes=['Documento p. 1'])
        original = copy.deepcopy(self.sample)
        result = evaluate(self.records, self.audit, self.sample)
        self.assertEqual(result['cobertura_por_grupo']['com_alerta']['avaliados'], 1)
        self.assertEqual(result['cobertura_por_grupo']['sem_alerta']['pendentes'], 2)
        self.assertEqual(result['linhas_para_segunda_conferencia'], [1])
        self.assertEqual(result['avaliados'], 1)
        self.assertEqual(result['pendentes'], 3)
        self.assertEqual(self.sample, original)
        result['casos'][0]['fontes'].append('Outra fonte')
        self.assertEqual(self.sample, original)

    def test_stale_duplicate_or_unsupported_decisions_rejected(self):
        for mutation in ('stale', 'duplicate', 'unsupported', 'string'):
            sample = copy.deepcopy(self.sample)
            if mutation == 'stale':
                sample['coleta_sha256'] = 'antigo'
            elif mutation == 'duplicate':
                sample['itens'].append(sample['itens'][0])
            else:
                sample['itens'][0]['exige_diligencia'] = True if mutation == 'unsupported' else 'false'
            with self.assertRaises(ValueError):
                evaluate(self.records, self.audit, sample)

    def test_sample_reproducible_and_both_groups_present(self):
        a = make_sample(self.records, self.audit, 1)
        self.assertEqual(a, make_sample(self.records, self.audit, 1))
        self.assertEqual(len(a['itens']), 2)
        self.assertEqual(sum(i['linha'] <= 2 for i in a['itens']), 1)

    def test_report_does_not_claim_success_for_pending_cases(self):
        report = render_report(evaluate(self.records, self.audit, self.sample))
        self.assertIn('Avaliados: 0. Pendentes: 4.', report)
        self.assertIn('Precisão: não calculável', report)
        self.assertIn('Casos pendentes não contam como acertos', report)

    def test_report_lists_both_kinds_of_disagreement(self):
        for item in self.sample['itens']:
            item.update(exige_diligencia=item['linha'] > 2, responsavel='Pessoa',
                        justificativa='Conferido', fontes=['Processo'])
        report = render_report(evaluate(self.records, self.audit, self.sample))
        self.assertIn('Linha 1: Alerta sem apoio', report)
        self.assertIn('Linha 3: Caso perdido', report)
        self.assertIn('Precisão: 0.00%', report)

    def test_cli_writes_report_and_preserves_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, value in [('contratos.json', self.records), ('parecer.json', self.audit),
                                ('referencia.json', self.sample)]:
                (root / name).write_text(json.dumps(value), encoding='utf-8')
            output, report = root / 'resultado.json', root / 'relatorio.md'
            argv = ['avaliar', '--execucao', str(root), '--referencia',
                    str(root / 'referencia.json'), '--saida', str(output), '--relatorio', str(report)]
            with patch('sys.argv', argv):
                main()
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['pendentes'], 4)
            self.assertIn('Avaliados: 0', report.read_text(encoding='utf-8'))
            saved = report.read_bytes()
            output.unlink()
            with patch('sys.argv', argv), self.assertRaises(SystemExit):
                main()
            self.assertFalse(output.exists())
            self.assertEqual(report.read_bytes(), saved)
