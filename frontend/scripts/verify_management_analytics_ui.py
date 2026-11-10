"""QA da análise pandas: ação simulada e leitura real, sem IA ou banco."""
import json
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:4174'
OUT = ROOT / 'frontend/qa'


if __name__ == '__main__':
    errors, calls = [], []
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1050})
        page.on('pageerror', lambda e: errors.append(str(e)))
        # Somente a ação POST é simulada: demais leituras usam o servidor real.
        def simulate(route):
            data = route.request.post_data_json
            assert data == {'action': 'gerar_indicadores', 'runId': '20261020T015002Z_72b23869'}
            calls.append(data)
            route.fulfill(status=202, content_type='application/json', body=json.dumps({
                'id': 'qa-analytics', 'action': data['action'], 'run_id': data['runId'],
                'status': 'concluido', 'active': False, 'resultado': {'indicadores': {
                    'linhas_coletadas': 450, 'linhas_elegiveis_distribuicao': 384, 'linhas_excluidas_distribuicao': 66}}}))
        page.route(BASE + '/api/jobs', simulate)
        page.goto(BASE)
        expect(page.get_by_label('Selecionar execução')).to_be_enabled()
        expect(page.get_by_label('Selecionar execução')).to_have_value('20261020T015002Z_72b23869')
        region = page.get_by_role('region', name='Indicadores de gestão', exact=True)
        expect(region.get_by_text('384 / 450', exact=True)).to_be_visible()
        expect(region.get_by_text('R$ 1.127.925.080,43', exact=True)).to_be_visible()
        expect(region.get_by_text('50,86%', exact=True)).to_be_visible()
        page.get_by_role('button', name='Gerar indicadores').click()
        expect(page.get_by_text('Gerar indicadores · Concluído', exact=True)).to_be_visible()
        region.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / 'analytics-desktop.png'), full_page=False)
        region.locator('summary').click()
        expect(region.locator('tbody tr')).to_have_count(10)
        region.get_by_role('button', name='Linha ', exact=False).first.click()
        expect(page.get_by_role('region', name='Indicadores deste contrato')).to_be_visible()
        page.get_by_role('button', name='Fechar detalhes').click()
        page.set_viewport_size({'width': 390, 'height': 844})
        region.evaluate('(el) => el.scrollIntoView({block: "start", behavior: "instant"})')
        page.screenshot(path=str(OUT / 'analytics-mobile.png'), animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert calls and not errors, errors
        browser.close()
    (OUT / 'analytics-ui-verificacao.json').write_text(json.dumps({'js_errors': errors, 'calls_simulados': calls,
        'leitura_real': True, 'desktop_mobile': True}), encoding='utf-8')
    print('Indicadores: leitura real, botão simulado, fontes por linha e mobile aprovados; zero erros JS.')
