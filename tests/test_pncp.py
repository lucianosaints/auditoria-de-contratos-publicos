import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from src.documents import DocumentSettings, digest, plan_documents, official_url
from src.pncp import (API, ORGAO, PncpSettings, PublicClient, catalog, collect_pncp,
                      document_links, file_links, money, official_file_url, reconcile)


def local():
    return {'Detalhe - Número': '15 - 2026', 'Detalhe - Processo': '200/2025',
            'Detalhe - CPF/CNPJ': '12.345.678/0001-99', 'Detalhe - Valor Inicial': 'R$ 100,00',
            'Detalhe - Assinatura': '01/02/2026'}


def remote(seq=1):
    return {'numeroContratoEmpenho': '00015/2026', 'anoContrato': 2026, 'sequencialContrato': seq,
            'numeroControlePNCP': f'{ORGAO}-2-{seq:06d}/2026', 'orgaoEntidade': {'cnpj': ORGAO},
            'processo': '00200/2025', 'niFornecedor': '12345678000199', 'valorInicial': 100,
            'dataAssinatura': '2026-02-01', 'numeroControlePncpCompra': f'{ORGAO}-1-000003/2026'}


def page(items, number=1, total=None, pages=1):
    return {'data': items, 'totalRegistros': len(items) if total is None else total,
            'totalPaginas': pages, 'numeroPagina': number}


class PncpTests(unittest.TestCase):
    def test_strict_identity_ambiguity_conflict_and_missing_coverage(self):
        rec, rem = local(), remote()
        result = lambda records, complete=True: reconcile([rec], [1], records, complete)[0]['situacao']
        self.assertEqual(result([rem]), 'confirmado_por_regras')
        self.assertEqual(result([rem, remote(2)]), 'candidato')
        self.assertEqual(result([rem], False), 'candidato')
        for key, value in [('processo', '201/2025'), ('niFornecedor', '99999999000199'), ('valorInicial', 101),
                           ('dataAssinatura', '2026-02-02')]:
            self.assertEqual(result([{**rem, key: value}]), 'conflitante')
        self.assertEqual(result([{**rem, 'niFornecedor': None}]), 'candidato')
        self.assertEqual(result([]), 'nao_localizado_no_recorte')
        self.assertEqual(result([], False), 'consulta_incompleta')
        self.assertEqual(money(0), 0)

    def test_catalog_requires_all_pages_consistent_totals_and_unique_ids(self):
        settings = PncpSettings()
        client = Mock()
        client.get.side_effect = [page([remote()], total=2, pages=2), page([remote(2)], 2, 2, 2)]
        self.assertTrue(catalog(client, '20260101', '20261021', settings)['completo'])
        for second in [page([remote()], 2, 2, 2), page([], 2, 2, 2), page([remote(2)], 2, 3, 2)]:
            client.get.side_effect = [page([remote()], total=2, pages=2), second]
            self.assertFalse(catalog(client, '20260101', '20261021', settings)['completo'])
        client.get.side_effect = [page([remote()], total=2, pages=2)]
        self.assertFalse(catalog(client, '20260101', '20261021', PncpSettings(max_pages=1))['completo'])

    def test_files_must_belong_to_contract_or_associated_purchase(self):
        match = reconcile([local()], [1], [remote()], True)[0]['candidatos'][0]
        base = f'https://pncp.gov.br/pncp-api/v1/orgaos/{ORGAO}'
        good = f'{base}/contratos/2026/1/arquivos/1'
        self.assertTrue(official_url(good))
        self.assertEqual(len(file_links([{'url': good, 'sequencialDocumento': 1}], match, PncpSettings())[0]), 1)
        for url in ['https://evil.test/a.pdf', good.replace('/1/arquivos', '/2/arquivos'), good + '?redirect=evil',
                    good.replace('pncp.gov.br/', 'pncp.gov.br.evil.test/')]:
            with self.assertRaises(ValueError):
                file_links([{'url': url, 'sequencialDocumento': 1}], match, PncpSettings())
        self.assertFalse(official_file_url('https://pncp.gov.br/admin'))

    def test_collection_checkpoint_document_plan_and_stale_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            audit = SimpleNamespace(suspeitos=[SimpleNamespace(linha=1)])
            url = f'https://pncp.gov.br/pncp-api/v1/orgaos/{ORGAO}/contratos/2026/1/arquivos/1'
            from unittest.mock import patch
            with patch.object(PublicClient, 'get', side_effect=[page([remote()]), [{'url': url, 'sequencialDocumento': 1}]]) as get:
                result = collect_pncp(folder, [local()], audit, session=Mock(), end=date(2026, 10, 21))
                self.assertEqual(get.call_count, 2)
            plan = plan_documents([local()], audit, DocumentSettings(), pncp=result)
            self.assertEqual(plan['documentos'], 1)
            self.assertEqual(plan['consultas'][0]['links'][0]['origem'], 'pncp')
            self.assertEqual(json.loads((folder / 'pncp.json').read_text(encoding='utf-8'))['status'], 'concluida')
            with self.assertRaises(ValueError):
                document_links(result, [{**local(), 'Objeto': 'mudou'}], [1])
            changed = copy.deepcopy(result)
            changed['consultas'][0]['situacao'] = 'candidato'
            changed['assinatura'] = digest({k: v for k, v in changed.items() if k != 'assinatura'})
            self.assertEqual(document_links(changed, [local()], [1]), {})

    def test_http_cache_hash_and_blocked_redirect(self):
        with tempfile.TemporaryDirectory() as directory:
            response = Mock(status_code=200, headers={})
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=None)
            response.iter_content.return_value = [json.dumps(page([remote()])).encode()]
            session = Mock(); session.get.return_value = response
            client = PublicClient(directory, PncpSettings(), session=session)
            url = f'{API}/orgaos/{ORGAO}/contratos/2026/1/arquivos'
            a = client.get(url)
            self.assertEqual(a, client.get(url))
            self.assertEqual(session.get.call_count, 1)
            cache = next((Path(directory) / 'pncp/cache').glob('*.json'))
            cached = json.loads(cache.read_text(encoding='utf-8')); cached['sha256'] = 'invalid'
            cache.write_text(json.dumps(cached), encoding='utf-8')
            response.status_code = 302
            with self.assertRaisesRegex(ValueError, 'HTTP 302'):
                client.get(url)
            self.assertFalse(session.get.call_args.kwargs['allow_redirects'])

    def test_interruption_publishes_recoverable_state(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            audit = SimpleNamespace(suspeitos=[SimpleNamespace(linha=1)])
            with patch.object(PublicClient, 'get', side_effect=[page([remote()]), KeyboardInterrupt()]):
                with self.assertRaises(KeyboardInterrupt):
                    collect_pncp(folder, [local()], audit, session=Mock(), end=date(2026, 10, 21))
            self.assertEqual(json.loads((folder / 'pncp.json').read_text(encoding='utf-8'))['status'], 'interrompida')
