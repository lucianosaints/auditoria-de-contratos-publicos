"""QA dos novos controles RAG/MCP e consulta, com dados fictícios."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:4173'
OUT = ROOT / 'frontend/qa'


def main():
    OUT.mkdir(exist_ok=True)
    dataset = {'id': 'qa-rag', 'records': [{'Processo': 'QA-RAG', 'Objeto': 'Objeto demonstrativo'}],
        'audit': {'linhas_analisadas': [1], 'suspeitos': [], 'relatorio_markdown': '# QA'}, 'demo': False,
        'documents': {'versao': 1, 'status': 'concluida', 'assinatura': 'qa', 'limite': 'QA', 'consultas': []}}
    meta = {'status': 'pronto', 'trechos': 8, 'paginas': 4, 'contratos': 1}
    state = {'job': None, 'calls': []}
    source = {'id': 'L1-Rqa', 'rotulo': 'Documento demonstrativo', 'pagina': 9, 'nota_tipo': 'Conferir original',
        'texto': 'Pagamento após entrega de 25 unidades. Trecho fictício para QA.', 'metodo': 'ocr_windows',
        'qualidade': 'conferir_imagem', 'documento_id': 'a'*64, 'sha256_pdf': 'b'*64, 'inicio': 600, 'fim': 670,
        'url': 'https://transparencia.marica.rj.gov.br/qa.pdf'}
    def api(route):
        path = route.request.url.split(BASE)[-1]
        def reply(value, code=200): route.fulfill(status=code, content_type='application/json', body=json.dumps(value))
        if path == '/api/runs': return reply([{'id': 'qa-rag', 'count': 1, 'hasAudit': True}])
        if path == '/api/runs/qa-rag': return reply(dataset)
        if path == '/api/control': return reply({'token': 'qa', 'jobs': [state['job']] if state['job'] else []})
        if path == '/api/runs/qa-rag/rag/status': return reply(meta)
        if path.startswith('/api/runs/qa-rag/rag/search?'):
            return reply({'linha': 1, 'fontes': [source], 'limite': 'Exemplo fictício. OCR exige conferir a imagem.'})
        if path == '/api/jobs':
            body = route.request.post_data_json; state['calls'].append(body)
            assert body['runId'] == 'qa-rag'
            summary = {'rag': meta} if body['action'] == 'preparar_rag' else {'mcp': {'ferramentas': ['estado_indice', 'buscar_evidencias']}}
            state['job'] = {'id': 'qa-' + str(len(state['calls'])), 'run_id': 'qa-rag', 'action': body['action'], 'status': 'concluido', 'active': False, 'finished_at': str(len(state['calls'])), 'resultado': summary}
            return reply(state['job'], 202)
        if path.startswith('/api/jobs/'): return reply(state['job'])
        return reply({'error': 'QA rota desconhecida'}, 404)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/api/**', api); page.goto(BASE)
        expect(page.get_by_role('button', name='Preparar RAG')).to_be_enabled()
        page.get_by_role('button', name='Preparar RAG').click()
        expect(page.get_by_text('RAG preparado:', exact=False)).to_be_visible()
        expect(page.get_by_role('button', name='Verificar MCP')).to_be_enabled()
        page.get_by_role('button', name='Verificar MCP').click()
        expect(page.get_by_text('MCP verificado por stdio', exact=False)).to_be_visible()
        page.get_by_label('Linha do contrato').fill('1')
        page.get_by_label('Termos para pesquisar').fill('medição pagamento')
        page.get_by_role('button', name='Buscar evidências').click()
        expect(page.get_by_text(source['texto'], exact=True)).to_be_visible()
        expect(page.get_by_role('link', name='Conferir PDF original')).to_have_attribute('href', '/api/runs/qa-rag/documentos/' + 'a'*64 + '#page=9')
        page.locator('.rag-search').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / 'rag-desktop.png'))
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('.rag-search').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(OUT / 'rag-mobile.png'))
        page.get_by_label('Selecionar execução').select_option('demo')
        expect(page.get_by_role('button', name='Preparar RAG')).to_be_disabled()
        expect(page.get_by_role('button', name='Verificar MCP')).to_be_disabled()
        assert [c['action'] for c in state['calls']] == ['preparar_rag', 'verificar_mcp']
        assert not errors, errors
        (OUT / 'rag-verificacao.json').write_text(json.dumps({'acoes': state['calls'], 'erros_js': errors, 'dados': 'ficticios'}, indent=2), encoding='utf-8')
        browser.close()
    print('QA RAG passou: botões, busca, fonte/página, execução selecionada e mobile.')


if __name__ == '__main__':
    main()
