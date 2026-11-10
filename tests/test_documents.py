import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.documents import (DocumentSettings, classify_document, collect_documents, digest, document_sources,
                           download_pdf, extract_pdf, inventory, official_url, plan_documents)

URL = 'https://transparencia.marica.rj.gov.br/teste.pdf'
PDF = b'%PDF-1.4\nDados demonstrativos'


def record(*urls):
    return {'Objeto': 'Objeto demonstrativo', 'Links publicados nos detalhes': json.dumps([
        {'url': url, 'rotulo': 'Contrato publicado'} for url in urls or (URL,)])}


def audit(*lines):
    return SimpleNamespace(suspeitos=[SimpleNamespace(linha=line) for line in lines or (1,)])


def extraction(path=None, settings=None):
    return {'status': 'lido', 'total_paginas': 1, 'avisos': [], 'paginas': [
        {'pagina': 1, 'texto': 'Contrato demonstrativo com objeto e condições documentais.',
         'metodo': 'texto_pdf', 'qualidade': 'texto_extraido_nao_validado', 'tabelas': [], 'aviso': None, 'truncado': False}]}


def session_for(content=PDF, status=200, headers=None):
    response = Mock(status_code=status, headers=headers or {})
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=None)
    response.iter_content.return_value = [content]
    session = Mock(); session.get.return_value = response
    return session


class DocumentTests(unittest.TestCase):
    def test_portal_export_is_distinguished_from_full_contract(self):
        value = extraction()
        value['paginas'][0]['texto'] = 'PORTAL DA TRANSPARÊNCIA DE MARICÁ Dados do Contrato'
        self.assertEqual(classify_document(value)['tipo_documento'], 'ficha_portal')
        self.assertIn('não é o instrumento contratual', value['nota_tipo'])
    def test_inventory_rejects_credentials_hosts_schemes_and_navigation(self):
        for url in ('http://transparencia.marica.rj.gov.br/x.pdf', 'https://127.0.0.1/x.pdf',
                    'https://transparencia.marica.rj.gov.br.evil.test/a.pdf', 'https://u:p@transparencia.marica.rj.gov.br/a.pdf'):
            self.assertIsNone(official_url(url))
        links, warnings = inventory(record(URL, URL, 'https://evil.test/a.pdf'))
        self.assertEqual(len(links), 1); self.assertTrue(warnings)
        self.assertEqual(inventory({'Links publicados nos detalhes': '[]'}), ([], []))
        self.assertTrue(inventory({'Links publicados nos detalhes': '{broken'})[1])
        self.assertEqual(inventory(record('https://transparencia.marica.rj.gov.br/1/visualizar'))[0], [])

    def test_plan_only_findings_deduplicates_and_exposes_limits(self):
        records = [record(URL, URL+'?a=2'), record(URL+'?a=3'), record(URL)]
        plan = plan_documents(records, audit(1, 3), DocumentSettings(max_links=1, max_documents=1))
        self.assertEqual(plan['documentos'], 1)
        self.assertEqual([e['linha'] for e in plan['consultas']], [1, 3])
        self.assertEqual(plan['links_omitidos'], 1)
        with self.assertRaises(ValueError): plan_documents(records, audit(0))

    def test_download_rejects_redirect_external_html_and_size(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'original.pdf'
            redirect = session_for(status=302, headers={'Location': 'https://evil.test/segredo'})
            with self.assertRaisesRegex(ValueError, 'domínio'): download_pdf(redirect, URL, path, DocumentSettings())
            self.assertEqual(redirect.get.call_count, 1)
            with self.assertRaisesRegex(ValueError, 'PDF legível'): download_pdf(session_for(b'<html>login</html>'), URL, path, DocumentSettings())
            with self.assertRaisesRegex(ValueError, '2 bytes'): download_pdf(session_for(PDF), URL, path, DocumentSettings(max_bytes=2))
            self.assertFalse(path.exists())

    def test_download_limit_checks_header_and_stream_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'original.pdf'
            path.write_bytes(b'original preservado')
            for headers in ({'Content-Length': '100'}, {}):
                with self.assertRaisesRegex(ValueError, '8 bytes'):
                    download_pdf(session_for(PDF, headers=headers), URL, path, DocumentSettings(max_bytes=8))
                self.assertEqual(path.read_bytes(), b'original preservado')
            download_pdf(session_for(PDF), URL, path, DocumentSettings(max_bytes=len(PDF)))
            self.assertEqual(path.read_bytes(), PDF)

    def test_settings_reject_unbounded_sizes_and_allow_explicit_env_limit(self):
        for size in (0, -1, True, 51 * 1024 * 1024):
            with self.assertRaises(ValueError):
                DocumentSettings(max_bytes=size)
        with patch.dict('os.environ', {'DOCUMENT_MAX_MB': '25'}, clear=True):
            self.assertEqual(DocumentSettings.from_env().max_bytes, 25 * 1024 * 1024)

    def test_selective_interruption_keeps_manifest_documents_in_later_contracts(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, records = Path(temp), [record(URL), record(URL + '?outro=1')]
            first = collect_documents(folder, records, audit(1, 2), session=session_for(), extractor=extraction)
            selected = first['consultas'][0]['documentos'][0]['id']
            with self.assertRaises(KeyboardInterrupt):
                collect_documents(folder, records, audit(1, 2), DocumentSettings(max_bytes=20 * 1024 * 1024),
                    session=session_for(), extractor=Mock(side_effect=KeyboardInterrupt()), retry_ids=[selected])
            saved = json.loads((folder / 'documentos.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['status'], 'interrompida')
            self.assertEqual(saved['consultas'], first['consultas'])

    def test_selective_retry_rejects_cross_contract_document_even_with_updated_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, records = Path(temp), [record(URL), record(URL + '?outro=1')]
            first = collect_documents(folder, records, audit(1, 2), session=session_for(), extractor=extraction)
            selected = first['consultas'][0]['documentos'][0]['id']
            first['consultas'][1]['documentos'] = copy.deepcopy(first['consultas'][0]['documentos'])
            entry = first['consultas'][1]
            entry['assinatura'] = digest({k: v for k, v in entry.items() if k != 'assinatura'})
            path = folder / 'documentos.json'
            path.write_text(json.dumps(first), encoding='utf-8')
            saved = path.read_bytes()
            session = session_for()
            with self.assertRaisesRegex(ValueError, 'links do contrato'):
                collect_documents(folder, records, audit(1, 2), session=session, retry_ids=[selected])
            session.get.assert_not_called()
            self.assertEqual(path.read_bytes(), saved)

    def test_selective_retry_keeps_other_documents_and_rejects_stale_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, records = Path(temp), [record(URL, URL + '?segundo=1')]
            first = collect_documents(folder, records, audit(), session=session_for(), extractor=extraction)
            docs = first['consultas'][0]['documentos']
            selected = docs[1]['id']
            session, extractor = session_for(), Mock(side_effect=extraction)
            second = collect_documents(folder, records, audit(), DocumentSettings(max_bytes=20 * 1024 * 1024),
                session=session, extractor=extractor, retry_ids=[selected])
            self.assertEqual(second['consultas'][0]['documentos'][0], docs[0])
            self.assertEqual(second['documentos_preservados'], 1)
            self.assertEqual(second['documentos_processados'], 1)
            self.assertEqual(extractor.call_count, 1)
            session.get.assert_not_called()  # PDF íntegro reutilizado, nova extração limitada.
            saved = (folder / 'documentos.json').read_bytes()
            with self.assertRaises(ValueError):
                collect_documents(folder, [record(URL, URL + '?mudou=1')], audit(),
                    session=session, extractor=extractor, retry_ids=[selected])
            self.assertEqual((folder / 'documentos.json').read_bytes(), saved)
            (folder / 'documentos' / f'{docs[0]["id"]}.pdf').write_bytes(b'alterado')
            with self.assertRaisesRegex(ValueError, 'Original preservado'):
                collect_documents(folder, records, audit(), session=session, retry_ids=[selected])
            self.assertEqual((folder / 'documentos.json').read_bytes(), saved)

    def test_resume_reuses_hashed_pdf_and_invalidates_corrupt_original(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            original = folder / 'parecer.json'; original.write_text('preservado')
            session, extractor = session_for(), Mock(side_effect=extraction)
            first = collect_documents(folder, [record()], audit(), session=session, extractor=extractor)
            second = collect_documents(folder, [record()], audit(), session=session, extractor=extractor)
            archived = list((folder / 'documentos/historico').glob('*.json'))
            self.assertEqual(len(archived), 1)
            self.assertEqual(json.loads(archived[0].read_text(encoding='utf-8')), first)
            self.assertEqual(first['assinatura'], second['assinatura'])
            self.assertEqual(session.get.call_count, 1); self.assertEqual(extractor.call_count, 1)
            next((folder / 'documentos').glob('*.pdf')).write_bytes(b'corrompido')
            collect_documents(folder, [record()], audit(), session=session, extractor=extractor)
            self.assertEqual(session.get.call_count, 2)
            self.assertEqual(original.read_text(), 'preservado')
            next((folder / 'documentos').glob('*.json')).write_text('{cache ilegível', encoding='utf-8')
            recovered = collect_documents(folder, [record()], audit(), session=session, extractor=extractor)
            self.assertEqual(session.get.call_count, 3)
            self.assertEqual(recovered['status'], 'concluida')

    def test_interruption_publishes_checkpoint_and_resume_reuses_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, records = Path(temp), [record(URL, URL+'?segundo=1')]
            extractor = Mock(side_effect=[extraction(), KeyboardInterrupt()])
            with self.assertRaises(KeyboardInterrupt):
                collect_documents(folder, records, audit(), session=session_for(), extractor=extractor)
            saved = json.loads((folder / 'documentos.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['status'], 'interrompida')
            self.assertEqual(len(saved['consultas'][0]['documentos']), 1)
            session = session_for()
            result = collect_documents(folder, records, audit(), session=session, extractor=extraction)
            self.assertEqual(session.get.call_count, 1)
            self.assertEqual(result['status'], 'concluida')

    def test_failures_and_missing_links_are_explicit_and_retryable(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = session_for(b'HTML')
            result = collect_documents(Path(temp), [record(), {}], audit(1, 2), session=bad)
            self.assertEqual(result['status'], 'com_pendencias')
            self.assertEqual(result['consultas'][0]['documentos'][0]['status'], 'falhou')
            self.assertEqual(result['consultas'][1]['documentos'], [])
            collect_documents(Path(temp), [record()], audit(), session=bad)
            self.assertEqual(bad.get.call_count, 2)

    def test_source_budget_line_binding_and_citations(self):
        with tempfile.TemporaryDirectory() as temp:
            result = collect_documents(Path(temp), [record()], audit(), session=session_for(), extractor=extraction)
            sources, coverage = document_sources(result, 1, record())
            self.assertEqual(sources[0]['pagina'], 1)
            self.assertTrue(sources[0]['id'].startswith('L1-A'))
            self.assertEqual(coverage['status'], 'disponivel')
            self.assertEqual(document_sources(result, 2, record())[0], [])
            self.assertEqual(document_sources(result, 1, {'Objeto': 'outro'})[0], [])
            changed = copy.deepcopy(result)
            doc = changed['consultas'][0]['documentos'][0]
            doc['paginas'] = [{**doc['paginas'][0], 'pagina': i+1, 'texto': 'x' * 8000} for i in range(10)]
            sources, coverage = document_sources(changed, 1, record())
            self.assertEqual(sum(len(s['texto']) for s in sources), 5000)
            self.assertEqual(coverage['paginas_nao_incluidas'], 7)
            self.assertTrue(all(s['truncado'] for s in sources))

    def test_extract_preserves_native_ocr_quality_tables_and_page_limit(self):
        native = Mock(width=600, height=800, images=[])
        native.extract_text.return_value = 'Texto nativo com condições do contrato e valores para conferência.'
        native.extract_tables.return_value = [[['Unidade', 'Valor'], ['1', 'R$ 100,00']]]
        scanned = Mock(width=600, height=800, images=[{'x0': 0, 'x1': 600, 'top': 0, 'bottom': 800}])
        scanned.extract_text.return_value = ''
        scanned.extract_tables.return_value = []
        pdf = Mock(pages=[native, scanned, native])
        pdf.__enter__ = Mock(return_value=pdf); pdf.__exit__ = Mock(return_value=None)
        with patch('pdfplumber.open', return_value=pdf):
            result = extract_pdf(Path('teste.pdf'), DocumentSettings(max_pages=2), ocr=lambda *a: 'Texto reconhecido em imagem com valor sujeito à revisão humana.')
        self.assertEqual(result['status'], 'parcial')
        self.assertEqual(result['paginas'][0]['tabelas'][0][1][1], 'R$ 100,00')
        self.assertEqual(result['paginas'][1]['metodo'], 'ocr_windows')
        self.assertEqual(result['paginas'][1]['qualidade'], 'conferir_imagem')
        with patch('pdfplumber.open', return_value=pdf):
            failed = extract_pdf(Path('teste.pdf'), DocumentSettings(max_pages=2), ocr=Mock(side_effect=RuntimeError('Sem OCR')))
        self.assertIn('Sem OCR', failed['paginas'][1]['aviso'])

    def test_official_json_download_envelope_is_followed_but_external_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            pdf = session_for().get.return_value
            envelope = session_for(json.dumps({'url': URL}).encode(), headers={'Content-Type': 'application/json'}).get.return_value
            session = Mock(); session.get.side_effect = [envelope, pdf]
            path = Path(temp) / 'original.pdf'
            self.assertEqual(download_pdf(session, URL+'?download=1', path, DocumentSettings()), URL)
            self.assertEqual(path.read_bytes(), PDF)
            bad = session_for(b'{"url":"https://evil.test/file.pdf"}', headers={'Content-Type': 'application/json'})
            with self.assertRaisesRegex(ValueError, 'domínio'):
                download_pdf(bad, URL, path, DocumentSettings())
            self.assertEqual(bad.get.call_count, 1)

