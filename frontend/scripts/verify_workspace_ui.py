"""QA da navegação reorganizada: leitura real e ações exclusivamente simuladas."""
import hashlib
import json
import re
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / 'frontend/qa'
RUN = '20261020T015002Z_72b23869'
BASE = 'http://127.0.0.1:4173'
source = ROOT / 'data/reports' / RUN
names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'documentos.json', 'pncp.json', 'indicadores.json', 'financeiro.json', 'arquivamento.json']
hashes = lambda: {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
before = hashes()
state = {'job': None, 'posts': []}

def fulfill(route, data, status=200):
    route.fulfill(status=status, content_type='application/json', body=json.dumps(data))

def jobs(route):
    request = route.request
    if request.method == 'POST':
        state['posts'].append({'url': request.url, 'body': request.post_data_json})
        if request.url.endswith('/stop'):
            state['job'].update(status='parando', active=True)
        else:
            assert request.post_data_json == {'action': 'consultar_financeiro', 'runId': RUN}
            state['job'] = {'id': 'qa-workspace-job', 'action': 'consultar_financeiro', 'run_id': RUN,
                'status': 'em_andamento', 'active': True, 'started_at': '2026-10-21T20:00:00Z'}
        fulfill(route, state['job'], 202 if not request.url.endswith('/stop') else 200)
    else:
        fulfill(route, state['job'])

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1366, 'height': 768})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    # Nenhum clique de QA alcança o executor real.
    page.route('**/api/jobs**', jobs)
    page.route('**/api/control', lambda route: fulfill(route, {'token': 'qa-token', 'jobs': [state['job']] if state['job'] else []}))

    def navigate(label):
        if page.viewport_size['width'] <= 760:
            page.get_by_role('button', name='Abrir menu', exact=True).click()
        page.get_by_role('navigation', name='Navegação principal').get_by_role('button', name=re.compile('^' + re.escape(label) + r'(?:\s|$)')).click()

    page.goto(BASE, wait_until='networkidle')
    expect(page.get_by_role('heading', name='Visão geral da auditoria', exact=True)).to_be_visible()
    expect(page.get_by_role('region', name='Indicadores da execução')).to_be_visible()
    expect(page.get_by_role('button', name=re.compile('^Nova auditoria'))).to_have_count(0)
    expect(page.get_by_role('region', name='Consulta financeira', exact=True)).to_have_count(0)
    assert page.get_by_role('region', name='Indicadores da execução').bounding_box()['y'] < 450
    page.screenshot(path=str(OUT / 'workspace-overview-desktop.png'), animations='disabled')
    navigate('Contratos')
    expect(page.get_by_label('Buscar contrato, objeto ou fornecedor', exact=True)).to_be_visible()
    expect(page.get_by_role('heading', name='O que você precisa fazer?', exact=True)).to_have_count(0)
    navigate('Evidências')
    expect(page.get_by_role('tab', name='Documentos', exact=True)).to_have_attribute('aria-selected', 'true')
    page.get_by_role('tab', name='Financeiro', exact=True).click()
    finance = page.get_by_role('region', name='Consulta financeira', exact=True)
    expect(finance).to_be_visible()
    expect(page.get_by_role('region', name='Reconciliação PNCP', exact=True)).to_have_count(0)
    expect(page.get_by_role('button', name='Conferir conflito da linha 96', exact=True)).not_to_be_visible()
    page.locator('.financial-conflicts > summary').click()
    page.get_by_role('button', name='Conferir conflito da linha 96', exact=True).click()
    expect(page.get_by_role('region', name='Empenhos do contrato')).to_contain_text('7501/2026')
    page.get_by_role('button', name='Fechar detalhes', exact=True).click()
    page.locator('.financial-conflicts > summary').click()
    page.screenshot(path=str(OUT / 'workspace-evidence-desktop.png'), animations='disabled')
    page.get_by_role('tab', name='PNCP', exact=True).click()
    page.get_by_role('tab', name='PNCP', exact=True).press('ArrowRight')
    expect(page.get_by_role('tab', name='Financeiro', exact=True)).to_be_focused()
    expect(page.get_by_role('tab', name='Financeiro', exact=True)).to_have_attribute('aria-selected', 'true')
    page.get_by_role('tab', name='Busca local', exact=True).click()
    expect(page.get_by_role('heading', name='Buscar nos documentos', exact=True)).to_be_visible()
    navigate('Indicadores')
    expect(page.get_by_role('region', name='Indicadores de gestão', exact=True)).to_be_visible()
    expect(page.get_by_role('region', name='Consulta financeira', exact=True)).to_have_count(0)
    navigate('Relatório')
    expect(page.get_by_role('button', name='Baixar relatório', exact=True)).to_be_visible()
    navigate('Operações')
    expect(page.get_by_role('button', name=re.compile('^Nova auditoria'))).to_be_enabled()
    expect(page.get_by_role('button', name=re.compile('^Consultar financeiro'))).to_have_count(0)
    page.get_by_role('button', name='Fontes e documentos', exact=True).click()
    expect(page.get_by_role('button', name='Fontes e documentos', exact=True)).to_have_attribute('aria-pressed', 'true')
    expect(page.get_by_role('button', name='Auditoria', exact=True)).to_have_attribute('aria-pressed', 'false')
    expect(page.get_by_role('button', name=re.compile('^Consultar financeiro'))).to_be_enabled()
    expect(page.get_by_role('button', name=re.compile('^Verificar MCP'))).not_to_be_visible()
    page.screenshot(path=str(OUT / 'workspace-operations-desktop.png'), animations='disabled')
    page.get_by_role('button', name='Análise e revisão', exact=True).click()
    expect(page.get_by_role('button', name=re.compile('^Estimar revisão'))).to_be_visible()
    page.locator('.operation-advanced > summary').click()
    expect(page.get_by_role('button', name=re.compile('^Preparar RAG'))).to_be_visible()
    page.locator('.operation-advanced > summary').click()
    page.get_by_role('button', name='Fontes e documentos', exact=True).click()
    page.get_by_role('button', name=re.compile('^Consultar financeiro')).click()
    expect(page.get_by_label('Estado atual da execução', exact=True)).to_be_visible()
    navigate('Visão geral')
    strip = page.get_by_role('region', name='Acompanhamento da auditoria')
    expect(strip).to_contain_text('Consultar financeiro em andamento')
    strip.get_by_role('button', name='Interromper', exact=True).click()
    expect(strip).to_contain_text('Interrupção solicitada')
    assert len(state['posts']) == 2 and state['posts'][-1]['url'].endswith('/stop')
    state['job'].update(active=False, status='interrompido', finished_at='2026-10-21T20:01:00Z')
    expect(strip).to_contain_text('Nenhuma ação em andamento', timeout=10000)
    # Reload não dispara ações e o layout se adapta ao telefone.
    page.set_viewport_size({'width': 390, 'height': 844})
    page.reload(wait_until='networkidle')
    expect(page.get_by_role('region', name='Indicadores da execução')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUT / 'workspace-overview-mobile.png'), animations='disabled')
    navigate('Operações')
    page.get_by_role('button', name='Fontes e documentos', exact=True).click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUT / 'workspace-operations-mobile.png'), animations='disabled')
    navigate('Evidências')
    page.get_by_role('tab', name='Financeiro', exact=True).click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    assert before == hashes()
    (OUT / 'workspace-verificacao.json').write_text(json.dumps({'erros_js': errors, 'posts_simulados': state['posts'],
        'dados_reais_preservados': before == hashes(), 'abas_teclado': True, 'desktop_mobile': True,
        'operacao_preservada_ao_navegar': True, 'interrupcao_simulada': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print('Navegação, fontes, grupos de ações e interrupção simulada aprovados; zero erros JS e originais intactos.')
