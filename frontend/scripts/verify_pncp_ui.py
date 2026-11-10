"""QA desktop/mobile do PNCP com dados fictícios, sem serviços externos."""
import json
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:4174'
OUT = ROOT / 'frontend/qa'


def main():
    OUT.mkdir(exist_ok=True)
    record = {'Processo': 'QA-PNCP/2026', 'Objeto': 'Contrato fictício para conferir a interface', 'Valor': '100.00'}
    entry = {'linha': 1, 'registro_original': record, 'situacao': 'confirmado_por_regras',
             'status_documentos': 'consultado', 'documentos_omitidos': 0,
             'candidatos': [{'numero_controle_pncp': 'EXEMPLO-FICTICIO',
                            'fornecedor': 'Fornecedor demonstrativo', 'objeto': 'Objeto demonstrativo',
                            'url': 'https://pncp.gov.br/app/contratos/29131075000193/2026/1',
                            'comparacoes': [{'campo': 'processo', 'portal': '200/2025', 'pncp': '200/2025', 'resultado': 'igual'}]}],
             'documentos': [{'id': 'a' * 64, 'url': 'https://pncp.gov.br/pncp-api/v1/orgaos/29131075000193/contratos/2026/1/arquivos/1',
                            'rotulo': 'Instrumento demonstrativo', 'tipo_informado_pncp': 'Contrato'}]}
    pncp = {'versao': 1, 'linhas': [1], 'consultado_em': '2026-10-21T12:00:00Z',
            'recorte': {'data_inicial': '20260101', 'data_final': '20261021'}, 'catalogo': {'completo': True},
            'limite': 'Dados fictícios. Não localizado não demonstra falta de publicação.', 'consultas': [entry]}
    data = {'id': 'qa-pncp', 'demo': False, 'records': [record], 'pncp': pncp,
            'audit': {'linhas_analisadas': [1], 'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Diligência demonstrativa'}],
                      'relatorio_markdown': '# QA fictício'}}
    job, calls, errors = {}, [], []

    def fulfill(route, payload, status=200):
        route.fulfill(status=status, content_type='application/json', body=json.dumps(payload))

    def api(route):
        nonlocal job
        path = route.request.url.split(BASE)[-1]
        if path == '/api/control':
            return fulfill(route, {'token': 'qa-token', 'jobs': [job] if job else []})
        if path == '/api/runs':
            return fulfill(route, [{'id': data['id'], 'count': 1, 'hasAudit': True}])
        if path == '/api/runs/qa-pncp':
            return fulfill(route, data)
        if path == '/api/jobs' and route.request.method == 'POST':
            body = route.request.post_data_json
            calls.append(body)
            assert body == {'action': 'consultar_pncp', 'runId': 'qa-pncp'}
            job = {'id': 'qa-pncp-job', 'action': body['action'], 'run_id': 'qa-pncp',
                   'status': 'concluido', 'active': False, 'finished_at': '2026-10-21T12:00:00Z',
                   'resultado': {'pncp': {'confirmados': 1, 'contratos': 1, 'documentos_disponiveis': 1}}}
            return fulfill(route, job, 202)
        if path.startswith('/api/jobs/'):
            return fulfill(route, job)
        if '/revisoes/' in path:
            return fulfill(route, {'historico': [], 'registro_sha256': 'qa', 'documentos_assinatura': None, 'parecer_sha256': 'qa'})
        if path.endswith('/rag/status'):
            return fulfill(route, {'status': 'nao_preparado'})
        return fulfill(route, {}, 404)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1050})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/api/**', api)
        page.goto(BASE)
        expect(page.get_by_role('button', name='Consultar PNCP')).to_be_enabled()
        page.get_by_role('button', name='Consultar PNCP').click()
        expect(page.get_by_text('Consultar PNCP · Concluído', exact=True)).to_be_visible()
        expect(page.get_by_role('region', name='Reconciliação PNCP')).to_be_visible()
        page.screenshot(path=str(OUT / 'pncp-desktop.png'), full_page=True)
        page.get_by_role('button', name='Ver detalhes de QA-PNCP/2026').click()
        region = page.get_by_role('region', name='Fontes PNCP')
        expect(region.get_by_text('Vínculo confirmado por regras', exact=True)).to_be_visible()
        expect(region.get_by_text('Portal: 200/2025 · PNCP: 200/2025 · coincide')).to_be_visible()
        expect(region.get_by_role('link', name='Conferir contrato no PNCP')).to_have_attribute('href', entry['candidatos'][0]['url'])
        expect(region.get_by_text('Lista de links não significa leitura realizada.', exact=False)).to_be_visible()
        region.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / 'pncp-detail-desktop.png'))
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(region).to_be_visible()
        region.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / 'pncp-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('dialog').evaluate('(el) => el.scrollWidth <= el.clientWidth')
        page.get_by_role('button', name='Fechar detalhes').click()
        entry['situacao'] = 'conflitante'
        page.reload()
        page.get_by_role('button', name='Ver detalhes de QA-PNCP/2026').click()
        expect(page.get_by_text('Divergências entre as fontes', exact=True)).to_be_visible()
        expect(page.get_by_text('Os candidatos podem ser contratos diferentes', exact=False)).to_be_visible()
        assert calls and not errors, errors
        browser.close()
    (OUT / 'pncp-ui-verificacao.json').write_text(json.dumps({'calls': calls, 'js_errors': errors, 'desktop_mobile': True}), encoding='utf-8')
    print('PNCP UI: desktop, mobile, ação, links e divergências aprovados; zero erros JS.')


if __name__ == '__main__':
    main()
