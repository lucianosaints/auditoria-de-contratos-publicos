import tempfile
import unittest
import json
import os
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

from src.audit_models import Achado, ParecerAuditoria
from src.gazette import (GazetteSettings, consult_gazette, extract_pdf, gazette_report,
                        identifier, match_page, official_url, select_editions)


class GazetteTests(unittest.TestCase):
    def record(self):
        return {'Detalhe - Número': '013 - 2026', 'Detalhe - Processo': '20857/2025',
                'Nr [Nr Processo]': '13 [20857/2025]', 'Detalhe - CPF/CNPJ': '12.345.678/0001-90',
                'Detalhe - Assinatura': '19/10/2026'}

    def test_identifiers_do_not_confuse_contract_year_with_process_year(self):
        result = identifier(self.record())
        self.assertEqual(result['contrato'], '13/2026')
        self.assertEqual(result['processo'], '20857/2025')
        self.assertEqual(result['cnpj'], '12345678000190')
        self.assertIsNone(identifier({'Nr [Nr Processo]': '13 [20857/2025]'})['contrato'])
        self.assertIsNone(identifier({'Detalhe - CPF/CNPJ': '123.456.789-00'})['cnpj'])

    def test_owning_context_and_additional_identifier_are_required_for_reinforcement(self):
        text = 'EXTRATO DO CONTRATO N.º 0013/2026. Processo administrativo nº 20857/2025. CNPJ 12.345.678/0001-90. Serviços de manutenção.'
        results = match_page(text, identifier(self.record()))
        self.assertTrue(results)
        self.assertIn('processo_e_ano_no_trecho', results[0]['criterios'])
        self.assertIn('cnpj_no_trecho', results[0]['criterios'])
        self.assertEqual(results[0]['correspondencia'], 'candidata_com_identificador_adicional')

    def test_same_number_wrong_year_or_larger_number_is_not_a_match(self):
        ids = {'contrato': '13/2026', 'processo': None, 'cnpj': None}
        for text in ('CONTRATO Nº 13/2025', 'CONTRATO Nº 113/2026', 'LICITAÇÃO Nº 13/2026'):
            self.assertEqual(match_page(text, ids), [])

    def test_cnpj_elsewhere_in_page_does_not_reinforce_contract(self):
        text = 'CONTRATO Nº 13/2026. ' + 'outro assunto ' * 100 + 'CNPJ 12.345.678/0001-90.'
        results = match_page(text, identifier(self.record()))
        self.assertNotIn('cnpj_no_trecho', results[0]['criterios'])
        self.assertEqual(results[0]['correspondencia'], 'candidata_para_conferencia')

    def test_only_official_https_hosts_are_allowed(self):
        for url in ('http://www.marica.rj.gov.br/file', 'https://evil.example/file',
                    'https://www.marica.rj.gov.br.evil.example/file', 'https://user:pass@www.marica.rj.gov.br/file'):
            with self.assertRaises(ValueError):
                official_url(url)
        self.assertEqual(official_url('/dom/ed-145/'), 'https://www.marica.rj.gov.br/dom/ed-145/')

    def fake_client(self):
        edition = {'id': 1, 'titulo': 'ED.145', 'tipo': 'dom', 'data_catalogo': '2026-10-19',
                   'url': 'https://www.marica.rj.gov.br/dom/ed-145/'}
        client = Mock()
        client.catalog.return_value = ([edition], [{'fonte': 'dom', 'catalogo_parcial': True}])
        client.read_edition.return_value = {**edition, 'url_pdf': 'https://www.marica.rj.gov.br/ed145.pdf',
            'sha256_pdf': 'abc', 'total_paginas': 1, 'paginas_sem_texto': 0, 'limitado': False,
            'paginas': [{'pagina': 1, 'texto': 'EXTRATO DO CONTRATO Nº 13/2026. Processo 20857/2025.'}]}
        return client

    def test_only_flagged_lines_searched_with_page_source_and_cache(self):
        audit = ParecerAuditoria(linhas_analisadas=[1, 2], suspeitos=[Achado(linha=2, motivo_suspeita='Conferir')], relatorio_markdown='Original')
        client = self.fake_client()
        with tempfile.TemporaryDirectory() as directory:
            result = consult_gazette([{}, self.record()], audit, Path(directory), GazetteSettings(max_editions=1), client=client)
            self.assertEqual(result['status'], 'consulta_parcial')
            self.assertEqual([q['linha'] for q in result['consultas']], [2])
            hit = result['consultas'][0]['resultados'][0]
            self.assertEqual(hit['pagina'], 1)
            self.assertIn('url_pdf', hit)
            consult_gazette([{}, self.record()], audit, Path(directory), GazetteSettings(max_editions=1), client=client)
            client.catalog.assert_called_once()
            report = gazette_report('Original', result)
            self.assertIn('#page=1', report)
            self.assertEqual(gazette_report(report, result), report)

    def test_no_findings_makes_no_external_request(self):
        audit = ParecerAuditoria(linhas_analisadas=[], suspeitos=[], relatorio_markdown='Sem achados')
        client = self.fake_client()
        with tempfile.TemporaryDirectory() as directory:
            result = consult_gazette([], audit, Path(directory), client=client)
        self.assertEqual(result['status'], 'sem_achados')
        client.catalog.assert_not_called()

    def test_network_failure_does_not_assert_lack_of_publication(self):
        client = self.fake_client()
        client.read_edition.side_effect = RuntimeError('Indisponível')
        audit = ParecerAuditoria(linhas_analisadas=[1], suspeitos=[Achado(linha=1, motivo_suspeita='Conferir')], relatorio_markdown='Original')
        with tempfile.TemporaryDirectory() as directory:
            result = consult_gazette([self.record()], audit, Path(directory), client=client)
        self.assertEqual(result['status'], 'consulta_indisponivel')
        self.assertEqual(len(result['falhas']), 1)
        self.assertIn('não comprova', result['limite'])

    def test_journal_failure_does_not_block_archive_and_preserves_failure_status(self):
        from src.batch_pipeline import run_pipeline, BatchSettings
        audit = ParecerAuditoria(linhas_analisadas=[1], suspeitos=[], relatorio_markdown='Original')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'contratos.json').write_text('[{}]')
            (folder / 'parecer.json').write_text(audit.model_dump_json(), encoding='utf-8')
            (folder / 'progresso.json').write_text('{"status":"analise_concluida"}')
            with patch.dict(os.environ, {'GAZETTE_ENABLED': 'true'}), patch('src.batch_pipeline.audit_in_batches'), \
                 patch('src.gazette.enrich_saved_audit', side_effect=RuntimeError('Indisponivel')), \
                 patch('src.batch_pipeline.ArquivarContratosTool') as archive:
                archive.return_value._run.return_value = '{"ok":true,"inseridos":0}'
                result = run_pipeline(SimpleNamespace(model='test'), folder, BatchSettings(), resume=True)
                self.assertTrue(result['ok'])
                self.assertEqual(json.loads((folder / 'diario_oficial.json').read_text(encoding='utf-8'))['status'], 'consulta_indisponivel')
                archive.assert_called_once()

    def test_edition_selection_is_bounded_and_considers_signature_date(self):
        editions = [{'url': str(i), 'data_catalogo': date} for i, date in enumerate(('2026-01-02', '2026-06-01', '2026-10-19'))]
        selected = select_editions(editions, [{'identificadores': {'assinatura': '2026-06-02'}}], 2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]['data_catalogo'], '2026-06-01')

    @patch('pdfplumber.open')
    def test_pdf_extraction_keeps_pages_and_marks_scans_or_page_limit(self, open_pdf):
        pdf = open_pdf.return_value.__enter__.return_value
        text = Mock(); text.extract_text.return_value = 'CONTRATO Nº 13/2026. Processo 20857/2025.'
        scan = Mock(); scan.extract_text.return_value = ''
        pdf.pages = [text, scan, text]
        result = extract_pdf(b'fixture', 2)
        self.assertEqual([p['pagina'] for p in result['paginas']], [1, 2])
        self.assertEqual(result['paginas_sem_texto'], 1)
        self.assertTrue(result['limitado'])
        self.assertFalse(result['ocr_realizado'])

    @patch('pdfplumber.open')
    def test_two_column_gazette_does_not_mix_unrelated_identifiers(self, open_pdf):
        page = Mock(width=600, height=800)
        page.chars = [{'x0': 20, 'x1': 25, 'top': 100}] * 300 + [{'x0': 350, 'x1': 355, 'top': 100}] * 300
        left = Mock(); left.extract_text.return_value = 'EXTRATO DO CONTRATO Nº 13/2026.'
        right = Mock(); right.extract_text.return_value = 'PROCESSO Nº 20857/2025 DE OUTRA MATÉRIA.'
        page.crop.side_effect = [left, right]
        open_pdf.return_value.__enter__.return_value.pages = [page]
        result = extract_pdf(b'fixture', 1)
        self.assertEqual([p['coluna'] for p in result['paginas']], [1, 2])
        self.assertEqual([p['pagina'] for p in result['paginas']], [1, 1])
        hits = match_page(result['paginas'][0]['texto'], identifier(self.record()))
        self.assertNotIn('processo_e_ano_no_trecho', hits[0]['criterios'])
