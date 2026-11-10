"""Verificação local da build servida em 127.0.0.1:4173, sem Gemini/Supabase."""
import json
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv' / 'Lib' / 'site-packages'))
from playwright.sync_api import sync_playwright

OUTPUT = ROOT / 'frontend' / 'qa'
OUTPUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    response = page.goto('http://127.0.0.1:4173/', wait_until='networkidle')
    assert response.ok
    assert page.request.get('http://127.0.0.1:4173/api/runs').ok
    assert page.request.get('http://127.0.0.1:4173/api/runs/no_such_run').status == 404
    page.get_by_label('Selecionar execução').select_option('demo')
    page.get_by_text('Modo demonstração.', exact=True).wait_for()
    assert page.locator('tbody tr').count() == 6
    page.screenshot(path=str(OUTPUT / 'desktop.png'), full_page=True)
    page.get_by_role('button', name='Explorar indícios').click()
    assert page.locator('tbody tr').count() == 4
    page.get_by_label('Buscar contrato, objeto ou fornecedor').fill('DEMO-001')
    assert page.locator('tbody tr').count() == 1
    page.get_by_role('button', name='Ver detalhes de DEMO-001/2026').click()
    assert page.locator('dialog').is_visible()
    assert page.get_by_role('region', name='Resumo em linguagem simples').is_visible()
    assert page.get_by_text('O que isso significa na prática', exact=True).is_visible()
    page.screenshot(path=str(OUTPUT / 'summary-desktop.png'))
    page.get_by_text('Ver fundamentação técnica (1)', exact=True).click()
    assert page.get_by_text('Custos e vantajosidade', exact=False).is_visible()
    page.keyboard.press('Escape')
    assert not page.locator('dialog').is_visible()
    with page.expect_download() as download:
        page.get_by_role('button', name='Exportar seleção').click()
    assert download.value.suggested_filename.endswith('.csv')
    page.locator('.nav-item').filter(has_text='Relatório de auditoria').click()
    assert page.get_by_role('heading', name='Relatório demonstrativo', exact=True).is_visible()
    with page.expect_download() as download:
        page.get_by_role('button', name='Baixar relatório').click()
    assert download.value.suggested_filename.endswith('.md')
    records = [{'Processo': 'TESTE-UI', 'Objeto': 'Objeto importado', 'Valor': '1.234,56'}]
    audit = {'linhas_analisadas': [1], 'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Quantitativos ausentes no resumo'}], 'relatorio_markdown': '# Importação de teste'}
    gazette = {'status': 'consulta_parcial', 'edicoes_lidas': 1, 'limite': 'Consulta de teste com cobertura parcial.',
        'consultas': [{'linha': 1, 'status': 'candidatos_localizados', 'resultados': [{'edicao': 'Edição de teste', 'fonte': 'dom', 'pagina': 2,
        'trecho': 'Trecho demonstrativo de uma publicação, sem associação a fatos reais.', 'criterios': ['contrato_e_ano'],
        'url_pdf': 'https://www.marica.rj.gov.br/exemplo.pdf'}]}]}
    review = {'status': 'concluida', 'total_contratos': 1, 'nota': 'Revisão demonstrativa de teste.', 'itens': [{
        'linha': 1, 'situacao': 'necessita_documentos', 'explicacao_simples': 'É necessário obter o documento completo.',
        'limite': 'O resumo não comprova ausência no processo.', 'proxima_diligencia': 'Solicitar termo de referência.',
        'skills': ['documental', 'precos_e_escopo', 'revisao'], 'registro_original': records[0],
        'motivos_originais': ['Quantitativos ausentes no resumo'],
        'evidencias': [{'fonte_id': 'L1-P1', 'trecho': 'Objeto importado', 'fonte': {
            'rotulo': 'Objeto', 'tipo': 'campo_portal', 'texto': 'Objeto importado', 'url': None}}]}]}
    page.locator('input[type=file]').set_input_files([
        {'name': 'contratos.json', 'mimeType': 'application/json', 'buffer': json.dumps(records).encode()},
        {'name': 'parecer.json', 'mimeType': 'application/json', 'buffer': json.dumps(audit).encode()},
        {'name': 'diario_oficial.json', 'mimeType': 'application/json', 'buffer': json.dumps(gazette).encode()},
        {'name': 'revisao_agentes.json', 'mimeType': 'application/json', 'buffer': json.dumps(review).encode()},
    ])
    page.locator('.nav-item').filter(has_text='Contratos').click()
    assert page.locator('tbody tr').count() == 1
    assert page.get_by_role('button', name='Ver detalhes de TESTE-UI', exact=True).is_visible()
    page.get_by_role('button', name='Ver detalhes de TESTE-UI', exact=True).click()
    assert page.get_by_role('region', name='Consulta ao Diário Oficial').is_visible()
    assert page.get_by_text('Edição de teste · DOM', exact=True).is_visible()
    assert page.get_by_role('link', name='Abrir PDF da fonte').get_attribute('href').endswith('#page=2')
    assert page.get_by_role('region', name='Acompanhamento dos agentes').is_visible()
    assert page.get_by_role('region', name='Revisão por agentes especialistas').is_visible()
    assert page.get_by_text('Documentos necessários', exact=True).is_visible()
    page.get_by_text('Conferir citações e procedimentos (1)', exact=True).click()
    assert page.locator('.agent-citation blockquote').inner_text() == 'Objeto importado'
    page.get_by_role('region', name='Revisão por agentes especialistas').scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT / 'agents-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(OUTPUT / 'agents-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.set_viewport_size({'width': 1440, 'height': 1100})
    page.get_by_role('region', name='Consulta ao Diário Oficial').scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT / 'gazette-desktop.png'))
    page.keyboard.press('Escape')
    page.get_by_label('Selecionar execução').select_option('demo')
    page.locator('.nav-item').filter(has_text='Visão geral').click()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(250)  # Aguarda a transição do menu após alterar viewport.
    page.screenshot(path=str(OUTPUT / 'mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), page.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth,elements:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,c:e.className,right:e.getBoundingClientRect().right})).slice(-15)})")
    page.get_by_role('button', name='Abrir menu').click()
    assert page.locator('.sidebar.is-open').is_visible()
    page.locator('.nav-item').filter(has_text='Como analisamos').click()
    assert page.get_by_role('heading', name='Tecnologia para fazer perguntas melhores.').is_visible()
    assert not errors, errors
    print('UI: API local, demo, filtros, detalhes, agentes, citacoes, downloads, importacao e mobile passaram; sem erros JS.')
    browser.close()
