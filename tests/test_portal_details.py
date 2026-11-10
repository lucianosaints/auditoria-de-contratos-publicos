import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from src.tools.portal_details import enrich_contracts, parse_details, portal_link, row_details


BASE = 'https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao'
DETAIL = '''<div class="content"><h5>Dados do Contrato</h5>
<div><span class="width-100">CPF/CNPJ:</span><strong>12.345.678/0001-00</strong></div>
<div><span class="width-100">Instrumento:</span><strong>TERMO DE ADESÃO</strong></div>
<div><strong class="width-100">Itens:</strong><div>Nenhum item encontrado.</div></div>
<div><strong class="width-100">Documentos:</strong><div><a data-href="/documentos/1/download" href="#">Anexo</a></div></div>
<a href="#" data-href="/contrato/1/download">.pdf</a></div>'''


class PortalDetailsTests(unittest.TestCase):
    def test_object_and_access_link_preserved(self):
        row = BeautifulSoup('''<tr><td><a>Ver Objeto</a>
            <span class="aviso-resposta">Fornecimento de escolas modulares</span></td>
            <td><a href="/e-cidade/contratos/padrao/1/visualizar"><i class="fa-eye"></i></a></td></tr>''', 'html.parser')
        fields = row_details(row, BASE)
        self.assertEqual(fields['Objeto'], 'Fornecimento de escolas modulares')
        self.assertEqual(fields['URL do contrato'], BASE + '/1/visualizar')

    def test_detail_fields_sections_and_download_links(self):
        fields = parse_details(DETAIL, BASE)
        self.assertEqual(fields['Detalhe - CPF/CNPJ'], '12.345.678/0001-00')
        self.assertEqual(fields['Detalhe - Instrumento'], 'TERMO DE ADESÃO')
        self.assertEqual(fields['Detalhe - Itens'], 'Nenhum item encontrado.')
        links = json.loads(fields['Links publicados nos detalhes'])
        self.assertEqual(len(links), 2)
        self.assertTrue(links[0]['url'].endswith('/documentos/1/download'))

    def test_external_and_non_web_links_rejected(self):
        for url in ('https://example.org/file', 'javascript:alert(1)', '#',
                    'https://user:secret@transparencia.marica.rj.gov.br/file'):
            self.assertIsNone(portal_link(url, BASE))

    def test_unrelated_page_is_not_contract_details(self):
        with self.assertRaises(ValueError):
            parse_details('<div class="content">Erro de acesso</div>', BASE)

    def test_enrichment_keeps_source_and_saves_html(self):
        browser = MagicMock()
        page = browser.new_page.return_value
        page.content.return_value = DETAIL
        records = [{'Objeto': 'Original', 'URL do contrato': BASE + '/1/visualizar'}]
        with tempfile.TemporaryDirectory() as directory:
            enrich_contracts(browser, records, Path(directory))
            self.assertEqual(records[0]['Objeto'], 'Original')
            self.assertEqual(records[0]['Status dos detalhes'], 'consultado')
            self.assertTrue((Path(directory) / records[0]['Arquivo HTML dos detalhes']).exists())
        page.close.assert_called_once()

    def test_enrichment_failure_and_missing_link_are_explicit(self):
        browser = MagicMock()
        browser.new_page.return_value.goto.side_effect = RuntimeError('Indisponível')
        records = [{'URL do contrato': BASE + '/1/visualizar'}, {}]
        enrich_contracts(browser, records)
        self.assertEqual(records[0]['Status dos detalhes'], 'falhou')
        self.assertEqual(records[1]['Status dos detalhes'], 'link não encontrado')


if __name__ == '__main__':
    unittest.main()
