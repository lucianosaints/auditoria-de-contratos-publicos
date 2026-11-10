"""QA de interface com amostra salva e POST simulado; nenhuma consulta externa."""
import copy
import json
import re
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / 'frontend/qa'
sample = ROOT / 'data/raw/financial_integration_20261021'
fixture = {'id': 'qa-financial', 'demo': False, 'records': json.loads((sample / 'contratos.json').read_text(encoding='utf-8')),
           'audit': json.loads((sample / 'parecer.json').read_text(encoding='utf-8')),
           'financial': json.loads((sample / 'financeiro.json').read_text(encoding='utf-8')), 'financialCurrent': True}
state = {'data': fixture, 'job': None, 'calls': []}

def fulfill(route, data, status=200):
    route.fulfill(status=status, content_type='application/json', body=json.dumps(data))

def jobs(route):
    if route.request.method == 'POST':
        body = route.request.post_data_json
        assert body == {'action': 'consultar_financeiro', 'runId': 'qa-financial'}
        state['calls'].append(body)
        state['job'] = {'id': 'qa-financial-job', 'action': body['action'], 'run_id': body['runId'],
                        'status': 'concluido', 'active': False, 'finished_at': '2026-10-21T19:40:00Z',
                        'resultado': {'financeiro': {'contratos': 1, 'detalhes': 2, 'conflitos': 2}}}
        fulfill(route, state['job'], 202)
    else:
        fulfill(route, state['job'])

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/runs', lambda route: fulfill(route, [{'id': 'qa-financial', 'count': 1, 'hasAudit': True}]))
    page.route('**/api/runs/qa-financial', lambda route: fulfill(route, state['data']))
    page.route('**/api/control', lambda route: fulfill(route, {'token': 'qa-token', 'jobs': [state['job']] if state['job'] else []}))
    page.route('**/api/jobs**', jobs)
    page.goto('http://127.0.0.1:4173', wait_until='networkidle')
    def navigate(label):
        if page.viewport_size['width'] <= 760:
            page.get_by_role('button', name='Abrir menu', exact=True).click()
        page.get_by_role('navigation', name='Navegação principal').get_by_role('button', name=label, exact=True).click()
    navigate('Operações')
    page.get_by_role('button', name='Fontes e documentos', exact=True).click()
    button = page.get_by_role('button', name=re.compile('^Consultar financeiro'))
    expect(button).to_be_enabled()
    button.click()
    expect(page.locator('.operation-history > summary')).to_contain_text('Consultar financeiro · Concluído')
    assert len(state['calls']) == 1
    navigate('Evidências')
    page.get_by_role('tab', name='Financeiro', exact=True).click()
    overview = page.get_by_role('region', name='Consulta financeira', exact=True)
    expect(overview).to_contain_text('1 contratos com conflito')
    overview.scroll_into_view_if_needed()
    overview.screenshot(path=str(OUT / 'financial-desktop.png'))
    page.locator('.financial-conflicts > summary').click()
    page.get_by_role('button', name='Conferir conflito da linha 1', exact=True).click()
    details = page.get_by_role('region', name='Empenhos do contrato', exact=True)
    expect(details).to_contain_text('5512/2026')
    expect(details).to_contain_text('3832/2021')
    expect(details).to_contain_text('Saldos rejeitados')
    expect(details).not_to_contain_text('R$ 1.934,97')
    page.set_viewport_size({'width': 390, 'height': 844})
    details.scroll_into_view_if_needed()
    details.screenshot(path=str(OUT / 'financial-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Fechar detalhes', exact=True).click()
    # Fonte obsoleta: não permite consultar saldos anteriores.
    state['data'] = {**fixture, 'financialCurrent': False}
    page.reload(wait_until='networkidle')
    navigate('Evidências')
    page.get_by_role('tab', name='Financeiro', exact=True).click()
    expect(page.get_by_text('Consulta financeira desatualizada ou incompatível', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='Conferir conflito da linha 1', exact=True)).to_have_count(0)
    assert not errors, errors
    (OUT / 'financial-ui-verificacao.json').write_text(json.dumps({'erros_js': errors, 'post_simulado': state['calls'],
        'conflito_sem_saldos': True, 'obsolescencia': True, 'mobile_sem_overflow': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print('QA financeiro desktop/mobile aprovado, POST simulado e zero erros JS.')
