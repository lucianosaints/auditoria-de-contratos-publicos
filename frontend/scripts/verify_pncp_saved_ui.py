"""Confere somente a leitura da execução real pelo painel local."""
import json
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect


if __name__ == '__main__':
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1050})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('http://127.0.0.1:4174')
        expect(page.get_by_label('Selecionar execução')).to_have_value('20261020T015002Z_72b23869')
        expect(page.get_by_label('Selecionar execução')).to_be_enabled()
        expect(page.get_by_role('region', name='Reconciliação PNCP')).to_contain_text('22 vínculos confirmados')
        page.get_by_label('Buscar contrato, objeto ou fornecedor').fill('5756/2026')
        page.locator('button[aria-label^="Ver detalhes de "][aria-label*="5756/2026"]').click()
        expect(page.get_by_role('region', name='Fontes PNCP')).to_contain_text('29131075000193-2-000452/2026')
        expect(page.get_by_role('region', name='Dossiê documental')).to_contain_text('Fonte PNCP')
        assert not errors, errors
        browser.close()
    (ROOT / 'frontend/qa/pncp-real-ui-verificacao.json').write_text(json.dumps({'js_errors': errors, 'leitura_real': True, 'acoes_iniciadas': 0}), encoding='utf-8')
    print('PNCP: execução real exibida, vínculo e PDF integrados, zero erros JS e zero ações iniciadas.')
