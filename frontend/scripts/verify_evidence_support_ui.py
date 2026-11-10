"""QA visual e funcional da cobertura e dos avisos, com dados fictícios."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.evidence_support import check_item

BASE = 'http://127.0.0.1:4173'
OUT = ROOT / 'frontend/qa'


def main():
    OUT.mkdir(exist_ok=True)
    record = {'Processo': 'QA-SUPORTE/2026', 'Objeto': 'Cooperação demonstrativa', 'Valor': 'R$ 0,00'}
    item = {'linha': 1, 'situacao': 'contextualizado', 'explicacao_simples': 'O ajuste não envolve repasse financeiro direto.',
        'limite': 'Restrito ao portal.', 'proxima_diligencia': 'Solicitar instrumento integral.', 'skills': ['documental'],
        'registro_original': record, 'motivos_originais': ['Conferir o valor zero.'],
        'evidencias': [{'fonte_id': 'L1-P1', 'trecho': 'R$ 0,00', 'fonte': {'id': 'L1-P1', 'texto': 'R$ 0,00',
            'tipo': 'campo_portal', 'rotulo': 'Valor publicado', 'truncado': False}}]}
    data = {'id': 'qa-support', 'demo': False, 'records': [record], 'audit': {'linhas_analisadas': [1],
        'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Conferir o valor zero.'}], 'relatorio_markdown': '# QA'},
        'review': {'versao': 1, 'status': 'concluida', 'atualizado_em': 'qa-v1', 'total_contratos': 1,
            'nota': 'Exemplo fictício.', 'rag_transporte': None, 'itens': [item], 'incremental': True,
            'contratos_reaproveitados': 1, 'contratos_pendentes': 0}}
    state = {'job': None, 'calls': []}
    def api(route):
        path = route.request.url.split(BASE)[-1]
        def reply(value, status=200): route.fulfill(status=status, content_type='application/json', body=json.dumps(value))
        if path == '/api/runs': return reply([{'id': 'qa-support', 'count': 1, 'hasAudit': True}])
        if path == '/api/runs/qa-support': return reply(data)
        if path == '/api/control': return reply({'token': 'qa-token', 'jobs': [state['job']] if state['job'] else []})
        if path == '/api/runs/qa-support/rag/status': return reply({'status': 'nao_preparado'})
        if path == '/api/jobs':
            body = route.request.post_data_json; state['calls'].append(body)
            assert body == {'action': 'conferir_suporte', 'runId': 'qa-support'}
            data['verification'] = {'versao': 1, 'revisao_atualizado_em': 'qa-v1', 'itens': [check_item(json.loads(json.dumps(item)))]}
            state['job'] = {'id': 'qa-check', 'action': 'conferir_suporte', 'run_id': 'qa-support', 'status': 'concluido',
                'active': False, 'finished_at': 'qa', 'resultado': {'suporte_verificado': 1, 'suporte_com_avisos': 1}}
            return reply(state['job'], 202)
        if path.startswith('/api/jobs/'): return reply(state['job'])
        if '/revisoes/' in path: return reply({'historico': []})
        return reply({'error': 'Rota QA não reconhecida'}, 404)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/api/**', api); page.goto(BASE)
        expect(page.get_by_text('Retomada por contrato: 1 reaproveitados', exact=False)).to_be_visible()
        page.get_by_role('button', name='Ver detalhes de QA-SUPORTE/2026').click()
        expect(page.get_by_text('RAG/MCP não utilizado nesta revisão.', exact=True)).to_be_visible()
        expect(page.get_by_text('Conferência ainda não disponível ou desatualizada.', exact=False)).to_be_visible()
        page.get_by_role('button', name='Fechar detalhes').click()
        page.get_by_role('button', name='Conferir suporte', exact=False).click()
        expect(page.get_by_text('1 contratos conferidos por regras', exact=False)).to_be_visible()
        expect(page.get_by_text('Suporte conferido por regras: 1/1', exact=False)).to_be_visible()
        page.get_by_role('button', name='Conferir avisos da linha 1').click()
        expect(page.get_by_text('Conclusão exige conferência humana', exact=True)).to_be_visible()
        expect(page.locator('.agent-explanation')).to_have_text(item['explicacao_simples'])
        expect(page.get_by_text('As citações não declaram explicitamente', exact=False)).to_be_visible()
        page.get_by_role('region', name='Fontes e suporte da conclusão').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / 'support-desktop.png'))
        page.set_viewport_size({'width': 390, 'height': 844})
        page.get_by_role('region', name='Fontes e suporte da conclusão').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('dialog').evaluate('(e) => e.scrollWidth <= e.clientWidth')
        page.screenshot(path=str(OUT / 'support-mobile.png'))
        item['explicacao_simples'] += ' Explicação alterada.'
        page.reload()
        page.get_by_role('button', name='Ver detalhes de QA-SUPORTE/2026').click()
        expect(page.get_by_text('Conferência ainda não disponível ou desatualizada.', exact=False)).to_be_visible()
        expect(page.get_by_text('Conclusão exige conferência humana', exact=True)).to_have_count(0)
        page.get_by_role('button', name='Fechar detalhes').click()
        page.get_by_label('Selecionar execução').select_option('demo')
        expect(page.get_by_role('button', name='Conferir suporte', exact=False)).to_be_disabled()
        assert len(state['calls']) == 1 and not errors, errors
        (OUT / 'support-verificacao.json').write_text(json.dumps({'acoes': state['calls'], 'erros_js': errors, 'dados': 'ficticios'}, indent=2), encoding='utf-8')
        browser.close()
    print('QA suporte passou: fontes, botão sem IA, avisos, preservação, obsolescência e mobile.')


if __name__ == '__main__':
    main()
