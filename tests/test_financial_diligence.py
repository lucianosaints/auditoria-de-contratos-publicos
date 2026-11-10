import copy
import unittest

from src.financial import digest
from src.financial_diligence import analyze_reference, build_diligence, request_text


class FinancialDiligenceTests(unittest.TestCase):
    def setUp(self):
        self.record = {'Detalhe - Número': '341 - 2026', 'Detalhe - Processo': '12242/2026',
                       'Detalhe - Contratado': 'CS BRASIL FROTAS S.A.', 'Detalhe - CPF/CNPJ': '27.595.780/0001-16'}
        self.text = ('EXTRATO DO CONTRATO N.º 341/2026. PROCESSO ADMINIS-\nTRATIVO N.º 12242/2026. '
                     'CS BRASIL FROTAS S.A. Programa de Trabalho: 68.01.06.181.0018.2076; '
                     'Elemento de Despesa: 3.3.3.9.0.39.00.00.00; Origem do Recurso: 1704; '
                     'Nota de Empenho: 4003/2026. Data da Assinatura: 01/09/2026.')

    def test_reference_is_support_not_financial_confirmation(self):
        result = analyze_reference(self.text, self.record, [4003, 2026])
        self.assertEqual(result['dotacao']['programa_trabalho'], '68.01.06.181.0018.2076')
        self.assertEqual(result['empenho_citado'], [4003, 2026])
        self.assertEqual(result['datas_assinatura_publicadas'], ['01/09/2026'])
        self.assertFalse(result['cnpj_localizado_no_escopo'])
        self.assertNotIn('saldos_publicados', result)
        self.assertTrue(analyze_reference(self.text + ' CNPJ 27.595.780/0001-16', self.record,
                                         [4003, 2026])['cnpj_localizado_no_escopo'])

    def test_other_contract_supplier_or_process_cannot_support_the_reference(self):
        for text in (self.text.replace('341/2026', '342/2026'),
                     self.text.replace('12242/2026', '12243/2026'),
                     self.text.replace('CS BRASIL FROTAS S.A.', 'Outra Empresa')):
            with self.assertRaises(ValueError):
                analyze_reference(text, self.record, [4003, 2026])

    def test_different_adjacent_encumbrance_and_malformed_year_are_not_chosen(self):
        for text in (self.text + ' Nota de Empenho: 4127/2026.',
                     self.text.replace('4003/2026', '4003/20260'),
                     self.text.replace('4003/2026', '4127/2026'),
                     self.text + ' Origem do Recurso: 1705;'):
            with self.assertRaises(ValueError):
                analyze_reference(text, self.record, [4003, 2026])

    def test_packet_keeps_rejection_and_human_review_pending_without_mutating_inputs(self):
        reference = {**analyze_reference(self.text, self.record, [4003, 2026]),
                     'registro_sha256': digest(self.record)}
        financial = {'coleta_sha256': 'origem', 'consultas': [{'linha': 1, 'vinculos': [{
            'numero_ano_esperado': [4003, 2026], 'numero_ano_observado': [776, 2024],
            'situacao': 'conflito_identidade', 'url': 'https://fonte', 'consultado_em': '2026-10-23'}]}]}
        financial['assinatura'] = digest(financial)
        original = copy.deepcopy(financial)
        packet = build_diligence([self.record], financial, 1, [reference], coleta_sha256='origem')
        self.assertEqual(packet['vinculos_publicados'][0]['situacao'], 'conflito_identidade')
        self.assertIsNone(packet['revisao_humana']['decisao'])
        self.assertIn('original_nao_obtido', packet['situacao'])
        self.assertIn('4003/2026', request_text(packet))
        self.assertIn('12242/2026', request_text(packet))
        self.assertEqual(financial, original)
        reference['empenho_citado'][0] = 999
        self.assertEqual(packet['referencias'][0]['empenho_citado'], [4003, 2026])
        with self.assertRaises(ValueError):
            build_diligence([self.record], financial, 1, [reference], coleta_sha256='outra_coleta')
