"""UI dos controles: estimativa REAL sem API/banco + demais ações simuladas."""
import hashlib
import json
import re
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv' / 'Lib' / 'site-packages'))
from playwright.sync_api import expect, sync_playwright

OUTPUT = ROOT / 'frontend' / 'qa'
OUTPUT.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:4173'
RUN = '20261020T015002Z_72b23869'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE, wait_until='networkidle')
    control = page.request.get(BASE + '/api/control').json()
    assert not any(j['active'] for j in control['jobs']), 'Existe uma ação do usuário em andamento; não iniciar teste.'
    source = ROOT / 'data' / 'reports' / RUN
    before = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in ('contratos.json', 'parecer.json', 'relatorio.md')}
    page.get_by_label('Selecionar execução').select_option(RUN)
    estimate = page.get_by_role('button', name=re.compile('^Estimar revisão'))
    expect(estimate).to_be_enabled()
    with page.expect_response(lambda r: r.url.endswith('/api/jobs') and r.request.method == 'POST') as started:
        estimate.click()
    assert started.value.status == 202, started.value.text()
    assert started.value.request.post_data_json == {'action': 'planejar_revisao', 'runId': RUN}
    job_id = started.value.json()['id']
    expect(page.get_by_text('Estimar revisão · Concluído', exact=True)).to_be_visible(timeout=90000)
    final_job = page.request.get(BASE + '/api/jobs/' + job_id).json()
    assert final_job['resultado']['contratos'] == 94
    assert final_job['resultado']['chamadas_maximas_de_etapas'] == 38
    assert before == {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in before}
    page.get_by_role('region', name='Executar ações da auditoria').scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT / 'controls-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(250)
    page.get_by_role('region', name='Executar ações da auditoria').scroll_into_view_if_needed()
    page.get_by_role('region', name='Executar ações da auditoria').screenshot(path=str(OUTPUT / 'controls-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    print('Planejamento REAL pelo botao passou: 94 contratos, 19 lotes, 38 chamadas estimadas; sem IA/banco e originais intactos.', flush=True)

    page.set_viewport_size({'width': 1440, 'height': 1100})
    state = {'job': None, 'calls': [], 'created': False, 'reject': False}
    records = [{'Processo': 'QA-SELECTED', 'Objeto': 'Objeto demonstrativo dos controles', 'Valor': '100.00'}]
    audit = {'linhas_analisadas': [1], 'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Conferir documentação'}], 'relatorio_markdown': '# QA controles'}
    def fixture(run_id):
        return {'id': run_id, 'records': records, 'audit': audit, 'progress': {'status': 'analise_concluida'}, 'demo': False}
    def fulfill(route, value, status=200):
        route.fulfill(status=status, content_type='application/json', body=json.dumps(value))
    def control_route(route):
        fulfill(route, {'token': 'qa-token', 'jobs': [state['job']] if state['job'] else []})
    def runs_route(route):
        fulfill(route, [{'id': run_id, 'count': 1, 'hasAudit': True} for run_id in (['qa-created', 'qa-selected', 'qa-other'] if state['created'] else ['qa-selected', 'qa-other'])])
    def job_route(route):
        request = route.request
        if request.method == 'GET':
            fulfill(route, {**state['job'], 'log': 'Acompanhamento demonstrativo, sem chamadas externas.'})
        elif request.url.endswith('/stop'):
            state['job'].update(status='parando', active=True)
            fulfill(route, state['job'])
        else:
            body = request.post_data_json
            state['calls'].append(body)
            if state['reject']:
                fulfill(route, {'error': 'Já existe uma ação em andamento.'}, 409)
                return
            action = body['action']
            target = 'qa-created' if action == 'nova_auditoria' else 'qa-selected'
            assert body == {'action': action, **({} if action == 'nova_auditoria' else {'runId': target})}
            active = action in {'retomar_auditoria', 'revisar_achados'}
            state['job'] = {'id': 'qa-job-' + str(len(state['calls'])), 'action': action, 'run_id': target,
                            'status': 'em_andamento' if active else 'concluido', 'active': active,
                            'finished_at': None if active else '2026-10-20T05:00:00Z'}
            if action == 'nova_auditoria': state['created'] = True
            fulfill(route, state['job'], 202)
    page.route('**/api/control', control_route)
    page.route('**/api/runs', runs_route)
    page.route('**/api/runs/*', lambda route: fulfill(route, fixture(route.request.url.rsplit('/', 1)[1])))
    page.route('**/api/jobs**', job_route)
    page.reload(wait_until='networkidle')
    expect(page.get_by_role('button', name='Retomar auditoria', exact=False)).to_be_enabled()
    page.get_by_role('button', name='Retomar auditoria', exact=False).click()
    expect(page.get_by_text('Retomar auditoria · Em andamento', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='Nova auditoria', exact=False)).to_be_disabled()
    page.get_by_role('button', name='Interromper', exact=True).click()
    expect(page.get_by_text('Retomar auditoria · Interrompendo', exact=True)).to_be_visible()
    state['job'].update(status='interrompido', active=False, finished_at='2026-10-20T05:00:01Z')
    expect(page.get_by_text('Retomar auditoria · Interrompido', exact=True)).to_be_visible(timeout=10000)
    expect(page.get_by_role('button', name='Consultar Diário', exact=False)).to_be_enabled()
    page.get_by_role('button', name='Consultar Diário', exact=False).click()
    expect(page.get_by_text('Consultar Diário · Concluído', exact=True)).to_be_visible()
    page.get_by_role('button', name='Revisar com agentes', exact=False).click()
    expect(page.get_by_text('Revisar com agentes · Em andamento', exact=True)).to_be_visible()
    page.reload(wait_until='networkidle')
    expect(page.get_by_text('Revisar com agentes · Em andamento', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='Nova auditoria', exact=False)).to_be_disabled()
    page.get_by_label('Selecionar execução').select_option('qa-other')
    state['job'].update(status='concluido', active=False, finished_at='2026-10-20T05:00:02Z')
    expect(page.get_by_text('Revisar com agentes · Concluído', exact=True)).to_be_visible(timeout=10000)
    expect(page.get_by_label('Selecionar execução')).to_have_value('qa-other')
    expect(page.get_by_role('button', name='Nova auditoria', exact=False)).to_be_enabled()
    page.get_by_role('button', name='Nova auditoria', exact=False).click()
    expect(page.get_by_label('Selecionar execução')).to_have_value('qa-created')
    page.get_by_label('Selecionar execução').select_option('qa-selected')
    expect(page.get_by_role('button', name='Revisar com agentes', exact=False)).to_be_enabled()
    state['reject'] = True
    page.get_by_role('button', name='Revisar com agentes', exact=False).click()
    expect(page.get_by_text('Já existe uma ação em andamento.', exact=True)).to_be_visible()
    page.locator('input[type=file]').set_input_files([
        {'name': 'contratos.json', 'mimeType': 'application/json', 'buffer': json.dumps(records).encode()},
        {'name': 'parecer.json', 'mimeType': 'application/json', 'buffer': json.dumps(audit).encode()},
    ])
    for label in ('Retomar auditoria', 'Consultar Diário', 'Revisar com agentes', 'Estimar revisão'):
        expect(page.get_by_role('button', name=re.compile('^' + label))).to_be_disabled()
    assert not errors, errors
    (OUTPUT / 'controls-verificacao.json').write_text(json.dumps({'planejamento_real': final_job,
        'originais_preservados': True, 'acoes_simuladas': state['calls'], 'erros_js': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('UI controles: nova, retomar, Diario, revisao, interrupcao, reload, selecao, importacao e erro passaram; sem acionar IA/banco.', flush=True)
    browser.close()
