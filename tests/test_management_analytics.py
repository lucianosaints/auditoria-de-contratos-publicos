import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.documents import digest
from src.management_analytics import analyze, build_indicators, cents, saved_indicators


def record(number='1', cnpj='00.123.456/0001-99', value='R$ 0,10', name='Fornecedor'):
    return {'Detalhe - Número': number + ' - 2026', 'Detalhe - Processo': number + '/2025',
            'Detalhe - CPF/CNPJ': cnpj, 'Detalhe - Contratado': name,
            'Detalhe - Valor Global': value, 'Objeto': 'Objeto demonstrativo'}


class ManagementAnalyticsTests(unittest.TestCase):
    def test_exact_sums_identifier_zeros_and_no_name_based_merge(self):
        records = [record(), record('2', value='0.20'), record('3', '99.123.456/0001-99', '0.30')]
        result = analyze(records)
        self.assertEqual(result['resumo']['valor_contratual_elegivel'], '0.60')
        self.assertEqual(len(result['fornecedores']), 2)
        self.assertEqual(result['fornecedores'][0]['cnpj'], '00123456000199')
        self.assertEqual(result['fornecedores'][0]['valor_contratual'], '0.30')
        self.assertEqual(result['fornecedores'][0]['participacao_percentual'], '50.00')
        self.assertEqual(result['execucao_financeira']['situacao'], 'nao_avaliavel')
        json.dumps(result, allow_nan=False)

    def test_large_integer_totals_do_not_overflow_or_round(self):
        result = analyze([record(value='92233720368547758.09'), record('2', value='0.01')])
        self.assertEqual(result['resumo']['valor_contratual_elegivel'], '92233720368547758.10')

    def test_absent_invalid_negative_and_repeated_id_are_excluded_without_guessing(self):
        repeated = record()
        rows = [repeated, copy.deepcopy(repeated), record('2', value=''),
                record('3', value='1.234'), record('4', value='-1.00'), record('5', cnpj='123.456.789-00')]
        result = analyze(rows)
        self.assertEqual(result['resumo']['linhas_identidade_repetida'], 2)
        self.assertEqual(result['resumo']['linhas_elegiveis_distribuicao'], 0)
        self.assertEqual(result['cobertura']['valores'], {'ausente': 1, 'invalido': 1, 'valido': 4})
        self.assertIsNone(result['resumo']['participacao_cinco_maiores_percentual'])
        self.assertEqual(cents('R$ 0,00'), (0, 'valido'))
        self.assertEqual(cents(1.23), (None, 'invalido'))
        self.assertIsNone(result['itens'][2]['valor_contratual'])

    def test_all_rows_remain_in_coverage_and_stale_documents_are_not_counted(self):
        records = [record(), record('2')]
        documents = {'consultas': [{'linha': 1, 'registro_sha256': 'antigo',
                                  'documentos': [{'status': 'lido', 'tipo_documento': 'pdf_publicado'}]}]}
        result = analyze(records, {'suspeitos': [{'linha': 1}]}, documents)
        self.assertEqual(len(result['itens']), 2)
        self.assertEqual(result['cobertura']['documentos'], {'fonte_desatualizada': 1, 'nao_processado': 1})
        self.assertEqual(result['itens'][0]['documentos_lidos_declarados'], 0)
        self.assertEqual(result['resumo']['linhas_com_alerta'], 1)
        with self.assertRaises(ValueError):
            analyze(records, documents={'consultas': [{'linha': 1}, {'linha': 1}]})

    def test_document_type_is_not_treated_as_validated_full_instrument(self):
        r = record()
        docs = {'consultas': [{'linha': 1, 'registro_sha256': digest(r), 'documentos': [
            {'status': 'lido', 'tipo_documento': 'ficha_portal'}, {'status': 'falhou'}]}]}
        self.assertEqual(analyze([r], documents=docs)['itens'][0]['cobertura_documental'], 'somente_fichas_ou_sem_tipo_validado')

    def test_saved_result_detects_source_changes_and_preserves_previous_version(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'contratos.json'
            source.write_text(json.dumps([record()]), encoding='utf-8')
            original = source.read_bytes()
            self.assertEqual(saved_indicators(folder)['status'], 'nao_preparado')
            build_indicators(folder)
            self.assertEqual(saved_indicators(folder, 1)['item']['linha'], 1)
            build_indicators(folder)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(len(list((folder / 'indicadores/historico').glob('*.json'))), 1)
            with self.assertRaises(ValueError):
                saved_indicators(folder, 2)
            source.write_text(json.dumps([record(value='2.00')]), encoding='utf-8')
            self.assertEqual(saved_indicators(folder)['status'], 'desatualizado')

    def test_empty_collection_has_no_invented_percentages(self):
        result = analyze([])
        self.assertEqual(result['resumo']['linhas_coletadas'], 0)
        self.assertEqual(result['fornecedores'], [])
        self.assertIsNone(result['resumo']['participacao_cinco_maiores_percentual'])
