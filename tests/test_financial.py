import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from src.financial import (SEARCH, HEADERS, FinancialClient, FinancialSettings, allowed_url,
    check_detail, collect_financial, digest, explicit_references, parse_detail, parse_listing, source_links,
    recheck_saved_detail)

SUPPLIER = '01234567000189'
URL = SEARCH + '/1/visualizar?origin=detailed-encumbrance-search'


def detail(number='22 - 2026'):
    return '<div class="content">Dados do Empenho' + ''.join(
        f'<div><span class="width-100">{k}:</span><strong>{v}</strong></div>' for k, v in
        [('Número', number), ('Instituição', 'PREFEITURA MUNICIPAL DE MARICA'), ('Empenhado', 'R$ 1.234,56'),
         ('Liquidado', 'R$ 0,00'), ('Anulado', 'não informado'), ('Pago', 'R$ 0,00')]) + '</div>'


def listing(supplier=SUPPLIER, year=2026):
    values = ['22/2026', '01/01/2026', 'Fornecedor', supplier, 'Secretaria', 'Licitação',
              '10/2026', 'PROCESSO: 15/2025', 'R$ 1.234,56', 'R$ 0,00', 'R$ 0,00',
              f'<a href="{URL}">Detalhar</a>']
    return (f'<form action="{SEARCH}/pesquisar"><input name="document" value="{supplier}">'
            f'<select name="year"><option value="{year}" selected>{year}</option></select></form>'
            '<table><thead><tr>' + ''.join(f'<th>{x}</th>' for x in HEADERS) + '</tr></thead><tbody><tr>' +
            ''.join(f'<td>{x}</td>' for x in values) + '</tr></tbody></table>')


def record():
    return {'Detalhe - Número': '3 - 2026', 'Detalhe - Processo': '15/2025', 'Detalhe - CPF/CNPJ': SUPPLIER}


class FinancialTests(unittest.TestCase):
    def prepare_recheck(self, folder):
        url = 'https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao/1/empenho'
        html = ('<div class="content">' + ''.join(
            f'<div><span class="width-100">{k}:</span><strong>{v}</strong></div>'
            for k, v in [('Número', '3 - 2026'), ('Processo', '15/2025'), ('CPF/CNPJ', SUPPLIER)]) +
            '<table><thead><tr><th>Número</th><th>Resumo</th><th>Detalhar</th></tr></thead>'
            f'<tbody><tr><td>22/2026</td><td>Resumo</td><td><a href="{url}">Ver</a></td></tr></tbody></table></div>')
        (folder / 'origem.html').write_text(html, encoding='utf-8')
        records = [{**record(), 'Arquivo HTML dos detalhes': 'origem.html'}] * 2
        for name, value in [('contratos.json', records), ('parecer.json', {'teste': True})]:
            (folder / name).write_text(json.dumps(value), encoding='utf-8')
        client = Mock()
        saved = {'consultado_em': '2026-10-21T00:00:00+00:00', 'sha256': 'a' * 64}
        client.listing.return_value = ([], saved)
        client.detail.return_value = (parse_detail(detail()), saved)
        result = collect_financial(folder, records,
            SimpleNamespace(suspeitos=[SimpleNamespace(linha=1), SimpleNamespace(linha=2)]), client=client)
        html = detail('776 - 2024')
        fresh = {'chave': ['detalhe', url], 'html': html, 'sha256': digest(html),
                 'consultado_em': '2026-10-23T00:00:00+00:00'}
        return result, url, fresh

    def test_recheck_rejects_changed_number_and_keeps_other_line_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            original, url, saved = self.prepare_recheck(folder)
            result = recheck_saved_detail(folder, 1, url, saved)
            self.assertEqual(result['consultas'][1], original['consultas'][1])
            link = result['consultas'][0]['vinculos'][0]
            self.assertEqual(link['situacao'], 'conflito_identidade')
            self.assertEqual(link['numero_ano_observado'], [776, 2024])
            self.assertNotIn('detalhe', link)
            self.assertEqual(result['detalhes_consultados'], original['detalhes_consultados'])
            self.assertEqual(result['consultas_fornecedores'], original['consultas_fornecedores'])
            self.assertEqual(result['assinatura'], digest({k: v for k, v in result.items() if k != 'assinatura'}))
            history = folder / 'financeiro/historico' / (digest(original) + '.json')
            self.assertEqual(json.loads(history.read_text(encoding='utf-8')), original)

    def test_recheck_invalid_sources_cannot_replace_saved_result(self):
        for mutation in ('hash', 'url', 'old_date', 'contract'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                _, url, saved = self.prepare_recheck(folder)
                before = (folder / 'financeiro.json').read_bytes()
                if mutation == 'hash': saved['html'] += 'alterado'
                elif mutation == 'url': saved['chave'][1] += '?outro=1'
                elif mutation == 'old_date': saved['consultado_em'] = '2020-01-01T00:00:00+00:00'
                else: (folder / 'origem.html').write_text('alterado')
                with self.assertRaises(ValueError):
                    recheck_saved_detail(folder, 1, url, saved)
                self.assertEqual((folder / 'financeiro.json').read_bytes(), before)

    def test_same_encumbrance_with_other_process_rejects_balances(self):
        data = parse_detail(detail('5342 - 2026'))
        data['campos']['Resumo'] = 'EM SUBSTITUIÇÃO A NOTA 4596/2026. CONTRATO Nº374/20260. P.A 7501/2026'
        result = check_detail([5342, 2026], data, {**record(), 'Detalhe - Processo': '17900/2025', 'Detalhe - Número': '376 - 2026'})
        self.assertEqual(result['situacao'], 'conflito_identidade')
        self.assertNotIn('detalhe', result)
        self.assertEqual(result['comparacoes'][0]['empenho'], [[7501, 2026]])
        self.assertEqual(result['comparacoes'][1]['referencias_invalidas'], ['374/20260'])

    def test_process_match_does_not_confirm_missing_supplier_or_contract(self):
        data = parse_detail(detail())
        data['campos']['Resumo'] = 'PROCESSO: 00015/2025'
        result = check_detail([22, 2026], data, record())
        self.assertEqual(result['situacao'], 'vinculo_pendente')
        self.assertEqual(result['comparacoes'][0]['resultado'], 'igual')
        self.assertEqual(result['comparacoes'][2]['resultado'], 'nao_comparavel')
        result = check_detail([22, 2026], data, record(), {'CPF/CNPJ': '99999999000199', 'Objeto': 'PROCESSO 15/2025'})
        self.assertEqual(result['situacao'], 'conflito_identidade')
        self.assertNotIn('detalhe', result)

    def test_reference_parser_never_repairs_year_or_chooses_between_processes(self):
        self.assertEqual(explicit_references('CONTRATO Nº374/20260', 'contrato'), {'validas': [], 'invalidas': ['374/20260']})
        self.assertEqual(explicit_references('P.A. 00015/2025. PROCESSO ADMINISTRATIVO Nº 19/2026', 'processo')['validas'], [[15, 2025], [19, 2026]])
        self.assertEqual(explicit_references('ATA 15/2025', 'processo')['validas'], [])
        data = parse_detail(detail()); data['campos']['Resumo'] = 'PROCESSO 15/2025. P.A 19/2026'
        result = check_detail([22, 2026], data, record())
        self.assertEqual(result['situacao'], 'vinculo_pendente')
        self.assertEqual(result['comparacoes'][0]['resultado'], 'ambiguo')

    def test_regression_misdirected_link_never_publishes_balances(self):
        rejected = check_detail((5512, 2026), parse_detail(detail('3832 - 2021')))
        self.assertEqual(rejected['situacao'], 'conflito_identidade')
        self.assertNotIn('detalhe', rejected)
        self.assertNotIn('saldos_publicados', rejected)
        accepted = check_detail((22, 2026), parse_detail(detail()))
        self.assertEqual(accepted['situacao'], 'vinculo_pendente')
        self.assertEqual(accepted['detalhe']['saldos_publicados']['Pago'], '0.00')
        self.assertIsNone(accepted['detalhe']['saldos_publicados']['Anulado'])

    def test_missing_or_ambiguous_identity_and_changed_schema_are_rejected(self):
        for html in [detail('não informado'), detail() + detail(), '<h1>Erro</h1>']:
            with self.assertRaises(ValueError):
                parse_detail(html)
        for html in [listing().replace('name="document"', 'name="other"'),
                     listing().replace('value="2026" selected', 'value="2025" selected'),
                     listing().replace('<th>Pago</th>', '<th>Outro</th>'),
                     listing().replace('<td>22/2026</td>', '<td>22/2025</td>')]:
            with self.assertRaises(ValueError):
                parse_listing(html, SUPPLIER, 2026)

    def test_listing_cnpj_zero_preserved_and_filter_not_inferred_from_url(self):
        self.assertEqual(parse_listing(listing(), SUPPLIER, 2026)[0]['CPF/CNPJ'], SUPPLIER)
        with self.assertRaises(ValueError):
            parse_listing(listing(), '99999999000199', 2026)
        with self.assertRaises(ValueError):
            parse_listing(listing().replace('</tbody>', listing().split('<tbody>')[1].split('</tbody>')[0] + '</tbody>'), SUPPLIER, 2026)

    def test_urls_reject_other_hosts_credentials_queries_and_routes(self):
        self.assertTrue(allowed_url(URL))
        self.assertTrue(allowed_url('https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao/26417/empenho'))
        for value in [URL.replace('https:', 'http:'), URL.replace('.gov.br/', '.gov.br.evil/'),
                      URL + '&redirect=evil', SEARCH + '/admin', URL.replace('https://', 'https://u:p@'),
                      URL + '#x', SEARCH + '?x=1']:
            self.assertFalse(allowed_url(value), value)

    def test_transport_redirects_and_byte_limit(self):
        response = Mock(status_code=302, headers={'Location': 'https://evil.test/a'})
        response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=None)
        session = Mock(); session.request.return_value = response
        with tempfile.TemporaryDirectory() as d:
            client = FinancialClient(d, FinancialSettings(max_bytes=1024), session)
            with self.assertRaisesRegex(ValueError, 'permitido'):
                client.request(SEARCH)
            self.assertEqual(session.request.call_count, 1)
            response.status_code = 200
            response.iter_content.return_value = [b'x' * 1025]
            with self.assertRaisesRegex(ValueError, 'bytes'):
                client.request(SEARCH)

    def test_cache_hash_expiry_and_reuse_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            client = FinancialClient(d, FinancialSettings(), Mock())
            loader = Mock(return_value=detail())
            client.cached(['test'], loader); client.cached(['test'], loader)
            self.assertEqual(loader.call_count, 1)
            path = next((Path(d) / 'financeiro/cache').glob('*.json'))
            saved = json.loads(path.read_text(encoding='utf-8')); saved['html'] = 'alterado'
            path.write_text(json.dumps(saved), encoding='utf-8')
            client.cached(['test'], loader)
            self.assertEqual(loader.call_count, 2)
            saved = json.loads(path.read_text(encoding='utf-8')); saved['consultado_em'] = '2000-01-01T00:00:00+00:00'
            path.write_text(json.dumps(saved), encoding='utf-8')
            client.cached(['test'], loader)
            self.assertEqual(loader.call_count, 3)

    def test_source_path_escape_and_incompatible_contract(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(source_links(d, {**record(), 'Arquivo HTML dos detalhes': '../elsewhere.html'}), ([], None))
            (Path(d) / 'source.html').write_text(detail(), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'incompatível'):
                source_links(d, {**record(), 'Arquivo HTML dos detalhes': 'source.html'})

    def test_collection_limits_failures_publication_and_originals_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            records = [record(), {**record(), 'Detalhe - CPF/CNPJ': '99999999000199'}]
            for name, data in [('contratos.json', records), ('parecer.json', {'teste': True})]:
                (folder / name).write_text(json.dumps(data), encoding='utf-8')
            before = {f.name: f.read_bytes() for f in folder.iterdir()}
            saved = {'consultado_em': '2026-10-21T00:00:00+00:00', 'sha256': 'a' * 64}
            client = Mock()
            client.listing.return_value = (parse_listing(listing(), SUPPLIER, 2026), saved)
            client.detail.return_value = (parse_detail(detail('3832 - 2021')), saved)
            audit = SimpleNamespace(suspeitos=[SimpleNamespace(linha=1), SimpleNamespace(linha=2)])
            result = collect_financial(folder, records, audit, FinancialSettings(max_suppliers=1, max_details=1), client)
            self.assertEqual(result['consultas'][0]['vinculos'][0]['situacao'], 'conflito_identidade')
            self.assertEqual(result['consultas'][1]['situacao_consulta'], 'limite_fornecedores')
            self.assertEqual(result['vinculos_confirmados'], 0)
            self.assertEqual(result['assinatura'], digest({k: v for k, v in result.items() if k != 'assinatura'}))
            self.assertEqual(before, {name: (folder / name).read_bytes() for name in before})
            client.listing.side_effect = ValueError('Filtros não confirmados')
            result = collect_financial(folder, records, audit, client=client)
            self.assertEqual(result['consultas'][0]['situacao_consulta'], 'consulta_falhou')
            self.assertTrue(list((folder / 'financeiro/historico').glob('*.json')))

    def test_interruption_keeps_recoverable_result(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / 'contratos.json').write_text('[{}]'); (folder / 'parecer.json').write_text('{}')
            client = Mock(); client.listing.side_effect = KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                collect_financial(folder, [record()], SimpleNamespace(suspeitos=[SimpleNamespace(linha=1)]), client=client)
            self.assertEqual(json.loads((folder / 'financeiro.json').read_text(encoding='utf-8'))['status'], 'interrompida')
