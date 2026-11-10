"""QA de interface com dados demonstrativos; sem portal, IA ou banco."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'frontend/qa'
BASE = 'http://127.0.0.1:4173'


def main():
    OUT.mkdir(exist_ok=True)
    record = {'Processo': 'QA-DOCUMENTOS/2026', 'Objeto': 'Documento demonstrativo para conferência humana', 'Valor': '100.00'}
    document = {'id': 'a'*64, 'url': 'https://transparencia.marica.rj.gov.br/qa.pdf', 'rotulo': 'Documento demonstrativo',
        'arquivo': 'documentos/'+'a'*64+'.pdf', 'sha256': 'b'*64, 'status': 'lido', 'total_paginas': 2,
        'nota_tipo': 'Exemplo fictício para verificação da interface.', 'avisos': [], 'paginas': [
            {'pagina': 1, 'texto': 'Texto demonstrativo da página um. Não representa contrato real.', 'metodo': 'texto_pdf', 'truncado': False,
             'aviso': None, 'tabelas': [[['Item', 'Valor'], ['Serviço demonstrativo', '100,00']]]},
            {'pagina': 2, 'texto': 'Trecho demonstrativo reconhecido por OCR.', 'metodo': 'ocr_windows', 'truncado': False,
             'aviso': 'Confira números e datas na imagem.', 'tabelas': []}]}
    manifest = {'versao': 1, 'status': 'concluida', 'assinatura': 'qa-docs', 'limite': 'Limites demonstrativos, sem dados reais.',
        'consultas': [{'linha': 1, 'registro_original': record, 'assinatura': 'qa-line', 'avisos': [], 'links_omitidos': 0, 'documentos': [document]}]}
    dataset = {'id': 'qa-documents', 'records': [record], 'audit': {'linhas_analisadas': [1], 'suspeitos': [
        {'linha': 1, 'motivo_suspeita': 'Conferir documentação demonstrativa'}], 'relatorio_markdown': '# QA demonstrativo'},
        'documents': manifest, 'demo': False}
    state = {'job': None, 'calls': [], 'history': []}
    errors = []
    def fulfill(route, data, code=200):
        route.fulfill(status=code, content_type='application/json', body=json.dumps(data))
    def api(route):
        request = route.request
        path = request.url.split(BASE)[-1]
        if path == '/api/control':
            return fulfill(route, {'token': 'qa-token', 'jobs': [state['job']] if state['job'] else []})
        if path == '/api/runs':
            return fulfill(route, [{'id': 'qa-documents', 'count': 1, 'hasAudit': True}])
        if path == '/api/runs/qa-documents': return fulfill(route, dataset)
        if path == '/api/jobs' and request.method == 'POST':
            body = request.post_data_json; state['calls'].append(body)
            assert body['runId'] == 'qa-documents'
            summary = {'documentos': 1, 'contratos': 1, 'contratos_sem_links': 0, 'links_omitidos': 0} if body['action'] == 'planejar_documentos' else {'documentos_processados': 1, 'status_documentos': 'concluida'}
            state['job'] = {'id': f'qa-job-{len(state["calls"])}', 'action': body['action'], 'run_id': body['runId'],
                'status': 'concluido', 'active': False, 'finished_at': str(len(state['calls'])), 'resultado': summary}
            return fulfill(route, state['job'], 202)
        if path.startswith('/api/jobs/'): return fulfill(route, state['job'])
        if path == '/api/runs/qa-documents/revisoes/1':
            if request.method == 'POST':
                body = request.post_data_json
                assert body['registro_sha256'] == 'qa-record' and body['parecer_sha256'] == 'qa-audit'
                state['history'].append({**body, 'id': f'event-{len(state["history"])+1}', 'registrado_em': '2026-10-20T23:00:00Z'})
            return fulfill(route, {'registro_sha256': 'qa-record', 'parecer_sha256': 'qa-audit', 'documentos_assinatura': 'qa-line', 'historico': state['history']}, 201 if request.method == 'POST' else 200)
        return fulfill(route, {'error': 'Rota de QA não reconhecida'}, 404)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/**', api)
        page.goto(BASE)
        expect(page.get_by_role('button', name='Planejar documentos')).to_be_enabled()
        page.get_by_role('button', name='Planejar documentos').click()
        expect(page.get_by_text('Planejar documentos · Concluído', exact=True)).to_be_visible()
        page.get_by_role('button', name='Ler documentos').click()
        expect(page.get_by_text('Ler documentos · Concluído', exact=True)).to_be_visible()
        page.get_by_role('button', name='Ver detalhes de QA-DOCUMENTOS/2026').click()
        expect(page.get_by_role('region', name='Dossiê documental')).to_be_visible()
        page.get_by_text('Página 1 · Texto do PDF', exact=True).click()
        expect(page.get_by_text('Serviço demonstrativo', exact=True)).to_be_visible()
        page.get_by_text('Página 2 · OCR local — conferir imagem', exact=True).click()
        expect(page.get_by_text('Confira números e datas na imagem.', exact=True)).to_be_visible()
        expect(page.get_by_role('link', name='Abrir PDF preservado')).to_have_attribute('href', '/api/runs/qa-documents/documentos/'+'a'*64)
        page.get_by_label('Responsável pela revisão').fill('Pessoa revisora — QA')
        page.get_by_label('Situação da revisão').select_option('documentos_solicitados')
        page.get_by_label('Justificativa da revisão').fill('Conferi a página e solicito os atestos. <script>não executar</script>')
        page.get_by_role('button', name='Salvar revisão humana').click()
        expect(page.get_by_text('Revisão registrada no histórico local.', exact=True)).to_be_visible()
        page.get_by_text('Histórico de revisões (1)', exact=True).click()
        expect(page.get_by_text('Conferi a página e solicito os atestos. <script>não executar</script>', exact=True)).to_be_visible()
        page.get_by_role('region', name='Registro de revisão humana').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT/'documents-desktop.png'))
        page.get_by_role('button', name='Fechar detalhes').click()
        page.get_by_role('button', name='Ver detalhes de QA-DOCUMENTOS/2026').click()
        page.get_by_text('Histórico de revisões (1)', exact=True).click()
        expect(page.get_by_text('Pessoa revisora — QA', exact=False)).to_be_visible()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.get_by_role('region', name='Registro de revisão humana').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('dialog').evaluate('(e) => e.scrollWidth <= e.clientWidth')
        page.screenshot(path=str(OUT/'documents-mobile.png'))
        page.get_by_role('button', name='Fechar detalhes').click()
        page.get_by_label('Selecionar execução').select_option('demo')
        expect(page.get_by_role('button', name='Ler documentos')).to_be_disabled()
        expect(page.get_by_role('button', name='Planejar documentos')).to_be_disabled()
        assert not errors, errors
        assert [c['action'] for c in state['calls']] == ['planejar_documentos', 'coletar_documentos']
        (OUT/'documents-verificacao.json').write_text(json.dumps({'erro_js': errors, 'acoes': state['calls'], 'revisoes': len(state['history']), 'dados': 'demonstrativos'}, ensure_ascii=False, indent=2), encoding='utf-8')
        browser.close()
    print('Interface documental passou: botões, páginas, tabelas, OCR, histórico, reabertura e mobile. Dados simulados.')


if __name__ == '__main__': main()
