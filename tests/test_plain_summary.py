import unittest

from src.audit_models import Achado, ParecerAuditoria
from src.plain_summary import build_summaries, plain_summary, report_with_summaries


class PlainSummaryTests(unittest.TestCase):
    def debt_record(self):
        return {'Nr [Nr Processo]': '57 [20857/2025]', 'Detalhe - Processo': '20857/2025',
                'Valor do Contrato': 'R$ 10579129.21',
                'Detalhe - Objeto': 'O MUNICÍPIO RECONHECE QUE TOMOU SERVIÇOS SEM COBERTURA CONTRATUAL, GERANDO CONTRAPRESTAÇÃO DE NATUREZA INDENIZATÓRIA.'}

    def test_debt_summary_uses_source_value_and_does_not_assert_payment(self):
        result = plain_summary(self.debt_record(), ['Reconhecimento de dívida; conferir medições'])
        self.assertEqual(result['tipo'], 'sem_cobertura')
        self.assertIn('R$ 10.579.129,21', result['em_resumo'])
        self.assertIn('reconhecimento de uma dívida', result['em_resumo'])
        self.assertIn('não comprova que ela já foi paga', result['significado_pratico'])
        self.assertIn('20857/2025', result['proxima_diligencia'])
        self.assertNotIn('57 [', result['proxima_diligencia'])

    def test_unverified_reason_is_not_recast_as_source_admission(self):
        result = plain_summary({'Objeto': 'Prestação de serviços', 'Valor': '100,00'}, ['Hipótese de serviços sem cobertura contratual'])
        self.assertEqual(result['tipo'], 'geral')
        self.assertNotIn('A própria descrição', result['problema_principal'])

    def test_only_confirmed_zero_can_use_zero_summary(self):
        for value in ('', '100,00', '1.234', 'inválido'):
            self.assertNotEqual(plain_summary({'Valor': value}, ['Valor zerado'])['tipo'], 'valor_zero')
        self.assertEqual(plain_summary({'Valor': 'R$ 0,00'}, ['Valor zerado'])['tipo'], 'valor_zero')

    def test_one_summary_per_flagged_contract_and_idempotent_report(self):
        record = self.debt_record()
        reason = 'Fundamentação técnica original preservada'
        audit = ParecerAuditoria(linhas_analisadas=[1, 2], suspeitos=[Achado(linha=1, motivo_suspeita=reason),
            Achado(linha=1, motivo_suspeita='Segundo achado'), Achado(linha=99, motivo_suspeita='Fora da coleta')],
            relatorio_markdown='# Relatório\n\n## Achados por linha global\n\n' + reason)
        summaries = build_summaries([record, {'Objeto': 'Sem achados'}], audit)
        self.assertEqual(len(summaries['achados']), 1)
        first = report_with_summaries(audit.relatorio_markdown, summaries)
        self.assertEqual(report_with_summaries(first, summaries), first)
        self.assertIn(reason, first)
        self.assertIn('Próxima diligência sugerida', first)
        self.assertEqual(report_with_summaries('# Sem achados', {'achados': []}), '# Sem achados')
