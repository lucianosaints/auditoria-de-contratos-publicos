import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crewai.tasks.task_output import TaskOutput

from src.tasks.audit_contracts import create_audit_task


class AuditEvidenceTests(unittest.TestCase):
    def validate(self, value, reason):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'parecer.json'
            (destination.parent / 'contratos.json').write_text(
                json.dumps([{'Valor do Contrato': value}]), encoding='utf-8')
            # Captura a função de validação da task sem criar agentes ou chamar LLM.
            with patch('src.tasks.audit_contracts.Task') as task:
                create_audit_task(None, None, destination)
                guardrail = task.call_args.kwargs['guardrail']
            output = TaskOutput(description='teste', agent='teste', raw=json.dumps({
                'linhas_analisadas': [1],
                'suspeitos': [{'linha': 1, 'motivo_suspeita': reason}],
                'relatorio_markdown': 'Relatorio de teste',
            }))
            return guardrail(output)

    def test_false_zero_is_rejected_without_inventing_overpricing(self):
        for value in ('R$ 81.176.157,77', '1234.56', ''):
            with self.subTest(value=value):
                ok, result = self.validate(value, 'Valor zerado em fornecimento oneroso')
                self.assertFalse(ok)
                self.assertNotIn('apresenta indício de sobrepreço', result)

    def test_actual_zero_remains_unchanged(self):
        reason = 'Valor zerado em fornecimento oneroso; conferir justificativa'
        ok, result = self.validate('0,00', reason)
        self.assertTrue(ok)
        self.assertEqual(json.loads(result)['suspeitos'][0]['motivo_suspeita'], reason)

    def test_information_gap_is_not_rewritten(self):
        reason = 'Quantitativos não publicados no resumo; solicitar planilha'
        ok, result = self.validate('R$ 81.176.157,77', reason)
        self.assertTrue(ok)
        self.assertEqual(json.loads(result)['suspeitos'][0]['motivo_suspeita'], reason)
