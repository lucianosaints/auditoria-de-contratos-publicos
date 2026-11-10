"""Andamento visível com fixtures: nenhuma auditoria/API de IA é executada."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parents[1] / 'qa'
BASE = 'http://127.0.0.1:4173'


def main():
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc)
    data = {'id': 'qa-status', 'demo': False, 'records': [{'Objeto': 'Exemplo de acompanhamento', 'Processo': 'QA/2026'}],
        'audit': {'linhas_analisadas': [1], 'suspeitos': [], 'relatorio_markdown': '# QA'},
        'progress': {'status': 'concluido', 'total_lotes': 32, 'lotes_concluidos': 32, 'linhas_concluidas': 450},
        'receipt': {'ok': True, 'recebidos': 94},
        'review': {'status': 'interrompida', 'total_contratos': 94, 'total_lotes': 19, 'lotes_concluidos': 0, 'itens': [],
                   'nota': 'Fixture demonstrativa.', 'erro': 'String should have at least 8 characters'}}
    job = {'id': 'qa-status-job', 'run_id': 'qa-status', 'action': 'revisar_achados', 'active': False,
           'status': 'falhou', 'finished_at': stamp.isoformat(), 'created_at': (stamp-timedelta(minutes=2)).isoformat()}
    errors = []
    def api(route):
        assert route.request.method == 'GET', 'O ensaio não pode executar ações.'
        path = route.request.url.split(BASE)[-1]
        if path == '/api/control': value = {'token': 'qa', 'jobs': [job]}
        elif path == '/api/runs': value = [{'id': 'qa-status', 'count': 1, 'hasAudit': True}]
        elif path == '/api/runs/qa-status': value = data
        elif path == '/api/jobs/qa-status-job': value = job
        else: value = {}
        route.fulfill(content_type='application/json', body=json.dumps(value))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/api/**', api)
        page.goto(BASE)
        banner = page.get_by_role('status', name='Estado atual da execução')
        expect(banner.get_by_text('Nenhuma ação em andamento', exact=True)).to_be_visible()
        expect(banner).to_contain_text('450 contratos analisados')
        expect(banner).to_contain_text('94 contratos arquivados')
        expect(banner).to_contain_text('citação curta sem o campo completo')
        banner.screenshot(path=str(OUT/'status-falha-desktop.png'))
        job.update(active=True, status='em_andamento', finished_at=None)
        data['review'].update(status='em_andamento', fase_atual='aguardando_intervalo', etapa_atual='investigacao',
            lote_atual=1, espera_ate=(datetime.now(timezone.utc)+timedelta(seconds=65)).isoformat())
        page.reload()
        expect(banner).to_contain_text('Revisar com agentes em andamento')
        expect(banner).to_contain_text('Pausa entre chamadas à IA')
        expect(banner).to_contain_text('Próxima tentativa em aproximadamente')
        expect(banner).to_contain_text('Tempo decorrido:')
        expect(banner.get_by_role('progressbar')).to_have_attribute('max', '19')
        data['review'].update(lotes_concluidos=1, lote_atual=2, fase_atual='chamando_ia')
        data['review'].pop('espera_ate')
        expect(banner).to_contain_text('1/19 lotes concluídos', timeout=15000)
        expect(banner).to_contain_text('Aguardando resposta da IA')
        page.set_viewport_size({'width': 390, 'height': 844})
        banner.scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        banner.screenshot(path=str(OUT/'status-ativo-mobile.png'))
        assert not errors, errors
        browser.close()
    print('Andamento passou: falha explícita, recibo, pausa, contagem, atualização automática e mobile; somente GETs simulados.')


if __name__ == '__main__': main()
