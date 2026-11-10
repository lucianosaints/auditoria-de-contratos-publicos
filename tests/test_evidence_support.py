import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.evidence_support import check_item, check_saved_review


def item(explanation='O ajuste não envolve repasse financeiro direto.', quote='R$ 0,00'):
    return {'linha': 1, 'situacao': 'contextualizado', 'explicacao_simples': explanation,
        'limite': 'Conferir o processo.', 'proxima_diligencia': 'Solicitar termo integral.',
        'registro_original': {'Objeto': 'Cooperação técnica'}, 'motivos_originais': ['Valor zero'], 'skills': [],
        'evidencias': [{'fonte_id': 'L1-P1', 'trecho': quote,
            'fonte': {'id': 'L1-P1', 'tipo': 'campo_portal', 'rotulo': 'Valor', 'texto': quote}}]}


class EvidenceSupportTests(unittest.TestCase):
    def test_zero_is_not_proof_of_absence_of_transfers(self):
        original = item()
        before = copy.deepcopy(original)
        checked = check_item(original)
        self.assertEqual(checked['avisos'][0]['codigo'], 'ausencia_financeira_sem_suporte')
        self.assertEqual(original, before)
        self.assertFalse(check_item(item(quote='O acordo não envolve repasse financeiro direto.'))['avisos'])
        self.assertTrue(check_item(item(quote='O acordo será celebrado sem ônus.'))['avisos'])
        self.assertTrue(check_item(item(quote='O texto não comprova ausência de repasse.'))['avisos'])

    def test_hypotheses_and_negative_legal_assertions_are_not_categorical_findings(self):
        for text in ['O valor zero pode indicar ausência de onerosidade.', 'O valor zero não comprova ausência de repasse.',
                     'Isso não constitui fraude.', 'Isso não é ilegalidade.', 'Há hipótese de fraude a verificar.']:
            self.assertFalse(check_item(item(explanation=text))['avisos'], text)
        self.assertTrue(check_item(item(explanation='Isso comprova fraude.'))['avisos'])

    def test_recognition_is_not_payment_and_negated_payment_does_not_support_it(self):
        text = 'O termo formaliza o reconhecimento da dívida e pagamento indenizatório.'
        self.assertEqual(check_item(item(text, 'Reconhecimento de dívida.'))['avisos'][0]['codigo'], 'pagamento_sem_comprovacao')
        self.assertTrue(check_item(item('O valor foi pago.', 'O valor não foi pago.'))['avisos'])
        self.assertTrue(check_item(item('O valor foi pago.', 'Solicitar comprovante de pagamento.'))['avisos'])
        self.assertFalse(check_item(item('O pagamento foi efetuado.', 'O pagamento foi efetuado em 20/10/2026.'))['avisos'])

    def test_nonliteral_and_wrong_contract_citations_are_marked(self):
        value = item('Valor publicado no portal.')
        value['evidencias'][0]['fonte']['texto'] = 'Outro texto'
        self.assertEqual(check_item(value)['avisos'][0]['codigo'], 'citacao_incompativel')
        value = item('Valor publicado no portal.')
        value['evidencias'][0]['fonte_id'] = 'L2-P1'
        self.assertTrue(check_item(value)['avisos'])

    def test_saved_check_and_ui_action_do_not_call_ai_or_modify_originals(self):
        from src.ui_jobs import execute_action
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'data/reports/selected'; folder.mkdir(parents=True)
            review = {'status': 'concluida', 'atualizado_em': 'qa', 'itens': [item()]}
            originals = {'contratos.json': [item()['registro_original']], 'parecer.json': {'linhas_analisadas': [1],
                'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Valor zero'}], 'relatorio_markdown': 'Original'}, 'revisao_agentes.json': review}
            for name, data in originals.items(): (folder / name).write_text(json.dumps(data), encoding='utf-8')
            before = {name: (folder / name).read_bytes() for name in originals}
            with patch('src.ui_jobs.ROOT', root), patch('src.main.create_audit_llm') as llm, patch('src.database.init_db') as db:
                code, summary = execute_action('conferir_suporte', 'selected')
                self.assertEqual(code, 0); self.assertEqual(summary['suporte_com_avisos'], 1)
                llm.assert_not_called(); db.assert_not_called()
            self.assertEqual(before, {name: (folder / name).read_bytes() for name in originals})
            self.assertTrue((folder / 'verificacao_evidencias.json').exists())
            changed = copy.deepcopy(review); changed['itens'][0]['registro_original']['Objeto'] = 'Outro'
            (folder / 'revisao_agentes.json').write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'mudaram'):
                check_saved_review(folder)
            (folder / 'revisao_agentes.json').write_text(json.dumps(review), encoding='utf-8')
            (folder / 'documentos.json').write_text(json.dumps({'assinatura': 'new'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fontes mudaram'):
                check_saved_review(folder)
