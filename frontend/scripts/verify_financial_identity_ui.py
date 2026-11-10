"""Verifica conflitos financeiros nos dados reais atuais; somente leitura."""
import json
import re
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / 'frontend/qa'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:4173', wait_until='networkidle')
    page.get_by_role('navigation', name='Navegação principal').get_by_role('button', name='Evidências', exact=True).click()
    page.get_by_role('tab', name='Financeiro', exact=True).click()
    page.locator('.financial-conflicts > summary').click()
    data = page.request.get('http://127.0.0.1:4173/api/runs/20261020T015002Z_72b23869').json()
    assert data['financialCurrent'] and data['financial']['politica_identidade'] == 2
    page.get_by_role('button', name='Conferir conflito da linha 96', exact=True).click()
    details = page.get_by_role('region', name='Empenhos do contrato', exact=True)
    expect(details).to_contain_text('17900/2025')
    expect(details).to_contain_text('7501/2026')
    expect(details).to_contain_text('374/20260')
    expect(details).not_to_contain_text('R$ 10.000.000,00')
    details.screenshot(path=str(OUT / 'financial-identity-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    details.screenshot(path=str(OUT / 'financial-identity-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Fechar detalhes', exact=True).click()
    page.set_viewport_size({'width': 1440, 'height': 1100})
    page.get_by_role('navigation', name='Navegação principal').get_by_role('button', name=re.compile('^Contratos')).click()
    page.get_by_label('Buscar contrato, objeto ou fornecedor', exact=True).fill('12242/2026')
    page.locator('tbody tr').filter(has_text='341 [12242/2026]').locator('button.row-open').click()
    details = page.get_by_role('region', name='Empenhos do contrato', exact=True)
    expect(details).to_contain_text('4003/2026')
    expect(details).to_contain_text('776/2024')
    expect(details).to_contain_text('Saldos rejeitados')
    expect(details).to_contain_text('23/10/2026')
    expect(details).not_to_contain_text('197.975,95')
    details.screenshot(path=str(OUT / 'financial-recheck-175-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    details.screenshot(path=str(OUT / 'financial-recheck-175-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    (OUT / 'financial-identity-verificacao.json').write_text(json.dumps({'politica': 2, 'linha_96_sem_saldos': True,
        'linha_175_rejeitada': True, 'erros_js': errors, 'mobile_sem_overflow': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print('Identidade financeira conferida em desktop/mobile, zero erros JS.')
