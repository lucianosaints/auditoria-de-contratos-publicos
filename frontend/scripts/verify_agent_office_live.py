"""Executor simulado: testa entregas reais na UI sem iniciar auditoria."""
import json
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect

state = {'job': None}
def reply(route, value):
    route.fulfill(content_type='application/json', body=json.dumps(value))

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors, writes = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: writes.append(r.url) if r.method != 'GET' else None)
    page.route('**/api/control', lambda r: reply(r, {'token': 'fixture', 'jobs': [state['job']] if state['job'] else []}))
    page.route('**/api/jobs/**', lambda r: reply(r, state['job']))
    page.goto('http://127.0.0.1:4173')
    page.wait_for_timeout(4000)
    run = page.get_by_role('combobox', name='Selecionar execução').input_value()
    assert run != 'demo'
    state['job'] = {'id': 'qa-live-office', 'run_id': run, 'action': 'nova_auditoria', 'active': True,
                    'status': 'em_andamento', 'office': {'agent': 0, 'phase': 'trabalhando', 'events': [{'seq': 1, 'agent': 0}]}}
    portal = {'name': 'Portal da Transparência de Maricá', 'url': 'https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao', 'status': 'consultando', 'started_at': 'fixture-1'}
    state['job']['office'].update(source=portal, sources=[portal])
    expect(page.get_by_text('Coletor trabalhando', exact=True)).to_be_visible(timeout=7000)
    sources = page.get_by_role('region', name='Fontes consultadas pelo Coletor')
    expect(sources.locator('.collector-source-url')).to_have_attribute('href', portal['url'])
    state['job']['office'] = {'agent': 1, 'phase': 'trabalhando', 'events': [{'seq': 1, 'agent': 0}, {'seq': 2, 'agent': 1}]}
    pncp = {'name': 'PNCP · contratos e anexos', 'url': 'https://pncp.gov.br/api/consulta/v1/contratos', 'status': 'cache_local', 'started_at': 'fixture-2'}
    state['job']['office'].update(source=pncp, sources=[{**portal, 'status': 'resposta_recebida'}, pncp])
    walker = page.locator('.office-walker[data-delivery-source="executor"]')
    expect(walker).to_be_visible(timeout=8000)
    assert walker.get_attribute('data-delivery-agent') == 'Coletor'
    assert walker.get_attribute('data-delivery-to') == 'Auditor'
    assert walker.locator('.office-held-document').count() == 1
    expect(sources.locator('.collector-source-url')).to_have_attribute('href', pncp['url'])
    expect(sources.locator('.collector-source-title').get_by_text('Reutilizando cache local', exact=True)).to_be_visible()
    assert sources.locator('.collector-source-history li').count() == 2
    state['job']['office']['phase'] = 'aguardando_cota'
    expect(page.get_by_text('Aguardando · animação pausada', exact=True)).to_be_visible(timeout=7000)
    stopped = walker.locator('.office-person').get_attribute('transform')
    page.wait_for_timeout(350)
    assert walker.locator('.office-person').get_attribute('transform') == stopped
    out = ROOT / 'frontend/qa'
    out.mkdir(exist_ok=True)
    page.get_by_role('region', name='Escritório 2D dos agentes').screenshot(path=str(out / 'agent-office-live.png'))
    sources.screenshot(path=str(out / 'agent-office-sources.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(350)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    sources.screenshot(path=str(out / 'agent-office-sources-mobile.png'))
    page.set_viewport_size({'width': 1440, 'height': 1100})
    state['job']['status'] = 'falhou'; state['job']['active'] = False
    expect(walker).to_have_count(0, timeout=7000)
    assert not errors, errors
    assert not writes, writes
    # O clique de início também é interceptado; não alcança o executor real.
    def start_fixture(route):
        if route.request.method == 'POST':
            assert route.request.post_data_json == {'action': 'nova_auditoria'}
            state['job'] = {'id': 'qa-office-start', 'run_id': 'qa-new-collection', 'action': 'nova_auditoria',
                'active': True, 'status': 'em_andamento', 'office': {'agent': 0, 'phase': 'trabalhando', 'events': [{'seq': 1, 'agent': 0}]}}
        reply(route, state['job'])
    page.route('**/api/jobs', start_fixture)
    page.get_by_role('button', name='Operações', exact=True).click()
    page.get_by_role('button', name='Nova auditoria', exact=False).click()
    expect(page.get_by_text('Coletor trabalhando', exact=True)).to_be_visible(timeout=7000)
    assert page.get_by_role('combobox', name='Selecionar execução').input_value() == 'qa-new-collection'
    assert page.get_by_role('button', name='Ver prévia do fluxo').is_disabled()
    assert len(writes) == 1, writes
    assert not errors, errors
    print('Início por clique, entrega, pausa por cota e falha aprovados; um POST interceptado, zero ações reais ou erros JS.')
    browser.close()
