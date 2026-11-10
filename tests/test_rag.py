import copy
import hashlib
import json
import tempfile
import sqlite3
from contextlib import closing
import unittest
from pathlib import Path
from src.rag import build_index, digest, search, status, run_folder


def fixture(folder):
    records = [{'Objeto': 'Serviço de manutenção.'}, {'Objeto': 'Aquisição de equipamentos.'}]
    (folder / 'documentos').mkdir()
    identifier = 'a' * 64
    pdf = b'%PDF-fixture-for-integrity-check'
    (folder / 'documentos' / (identifier + '.pdf')).write_bytes(pdf)
    doc = {'id': identifier, 'status': 'lido', 'sha256': hashlib.sha256(pdf).hexdigest(),
        'rotulo': 'Instrumento demonstrativo', 'url': 'https://transparencia.marica.rj.gov.br/qa.pdf',
        'tipo_documento': 'pdf_publicado', 'nota_tipo': 'Conferir original',
        'paginas': [{'pagina': 1, 'texto': 'Introdução sem os detalhes procurados. ' * 40,
            'metodo': 'texto_pdf', 'qualidade': 'texto_extraido_nao_validado', 'truncado': False, 'aviso': None},
            {'pagina': 9, 'texto': 'Cláusula de medição: pagamento após entrega de 25 unidades. Garantia de execução.',
            'metodo': 'ocr_windows', 'qualidade': 'conferir_imagem', 'truncado': False, 'aviso': None}]}
    manifest = {'assinatura': 'fixture', 'consultas': [
        {'linha': 1, 'registro_sha256': digest(records[0]), 'assinatura': 'entry', 'documentos': [doc]},
        {'linha': 2, 'registro_sha256': digest(records[1]), 'assinatura': 'entry2', 'documentos': [{**copy.deepcopy(doc),
            'paginas': [{**doc['paginas'][1], 'texto': 'Pagamento sigiloso exclusivo do segundo contrato.'}]}]}]}
    (folder / 'contratos.json').write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
    (folder / 'documentos.json').write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    return records, manifest


class RagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.records, self.manifest = fixture(self.folder)

    def test_retrieves_later_page_literal_and_never_other_contract(self):
        meta = build_index(self.folder)
        self.assertEqual(meta['contratos'], 2)
        found = search(self.folder, 1, 'medicao pagamento')
        self.assertEqual(found['fontes'][0]['pagina'], 9)
        self.assertEqual(found['fontes'][0]['texto'], self.manifest['consultas'][0]['documentos'][0]['paginas'][1]['texto'])
        self.assertEqual(found['fontes'][0]['qualidade'], 'conferir_imagem')
        self.assertTrue(all(s['linha'] == 1 for s in found['fontes']))
        self.assertEqual(search(self.folder, 1, 'sigiloso')['fontes'], [])
        self.assertEqual(len(search(self.folder, 2, 'sigiloso')['fontes']), 1)
        self.assertEqual(search(self.folder, 1, '" OR * NOT ()')['fontes'], [])

    def test_index_stale_when_content_changes_even_same_claimed_signature(self):
        build_index(self.folder)
        self.assertEqual(status(self.folder)['status'], 'pronto')
        self.manifest['consultas'][0]['documentos'][0]['paginas'][1]['texto'] += ' Alteração.'
        (self.folder / 'documentos.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        self.assertEqual(status(self.folder)['status'], 'desatualizado')
        with self.assertRaisesRegex(ValueError, 'desatualizado'):
            search(self.folder, 1, 'pagamento')

    def test_changed_pdf_refused_and_failed_build_keeps_previous_index(self):
        build_index(self.folder)
        original = (self.folder / 'rag/indice.sqlite3').read_bytes()
        (self.folder / 'documentos' / ('a'*64 + '.pdf')).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'PDF local mudou'):
            search(self.folder, 1, 'pagamento')
        with self.assertRaises(ValueError):
            build_index(self.folder)
        self.assertEqual((self.folder / 'rag/indice.sqlite3').read_bytes(), original)

    def test_record_mismatch_and_unsafe_scope_rejected(self):
        self.manifest['consultas'][0]['registro_sha256'] = 'wrong'
        (self.folder / 'documentos.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'incompatíveis'):
            build_index(self.folder)
        with self.assertRaises(ValueError):
            run_folder('../escape')

    def test_indexed_text_is_rechecked_against_manifest(self):
        build_index(self.folder)
        with closing(sqlite3.connect(self.folder / 'rag/indice.sqlite3')) as conn, conn:
            rows = conn.execute('SELECT id, fonte FROM trechos WHERE linha=1').fetchall()
            for identifier, raw in rows:
                value = json.loads(raw)
                value['texto'] = 'Conteúdo adulterado sem apoio no PDF.'
                conn.execute('UPDATE trechos SET fonte=? WHERE id=?', (json.dumps(value), identifier))
        with self.assertRaisesRegex(ValueError, 'incompatível'):
            search(self.folder, 1, 'pagamento')

    def test_agent_context_uses_retrieved_page_instead_of_first_page(self):
        from src.agent_review import build_dossiers, citation_catalog, validate_stage
        from src.audit_models import ParecerAuditoria, Achado
        from src.rag_client import retrieve_for_agents
        audit = ParecerAuditoria(linhas_analisadas=[1, 2], suspeitos=[Achado(linha=1, motivo_suspeita='Conferir medição e pagamento')], relatorio_markdown='QA')
        self.assertIsNone(retrieve_for_agents(self.folder, self.records, audit))
        build_index(self.folder)
        retrieved = {1: search(self.folder, 1, 'medição pagamento')}
        dossier = build_dossiers(self.records, audit, documents=self.manifest, retrieval=retrieved)[0]
        source = next(s for s in dossier['fontes'] if s.get('rag'))
        self.assertEqual(source['pagina'], 9)
        self.assertEqual(dossier['documentos']['transporte'], 'mcp_stdio')
        catalog = citation_catalog(dossier)
        choice = next(k for k, v in catalog.items() if v['fonte_id'] == source['id'])
        validated = validate_stage('investigacao', {'itens': [{'linha': 1, 'observacao': 'Conferir o original.',
            'limite': 'OCR sujeito a erros.', 'evidencias': [{'citacao_id': choice}]}]}, [dossier])
        self.assertEqual(validated['itens'][0]['evidencias'][0]['trecho'], source['texto'])

    def test_real_mcp_stdio_handshake_and_agent_retrieval_without_llm(self):
        from src.rag import ROOT
        from src.rag_client import check_connection, retrieve_for_agents
        from src.audit_models import ParecerAuditoria, Achado
        with tempfile.TemporaryDirectory(prefix='qa_rag_', dir=ROOT / 'data/reports') as name:
            folder = Path(name)
            records, _ = fixture(folder)
            build_index(folder)
            connection = check_connection(folder)
            self.assertTrue(connection['conectado'])
            self.assertEqual(set(connection['ferramentas']), {'estado_indice', 'buscar_evidencias', 'consultar_indicadores'})
            self.assertEqual(connection['indice']['status'], 'pronto')
            audit = ParecerAuditoria(linhas_analisadas=[1, 2], suspeitos=[
                Achado(linha=1, motivo_suspeita='medição'), Achado(linha=2, motivo_suspeita='sigiloso')], relatorio_markdown='QA')
            retrieved = retrieve_for_agents(folder, records, audit)
            self.assertEqual(retrieved[1]['fontes'][0]['pagina'], 9)
            self.assertIn('sigiloso', retrieved[2]['fontes'][0]['texto'])
            self.assertTrue(all(s['linha'] == 1 for s in retrieved[1]['fontes']))


if __name__ == '__main__':
    unittest.main()
