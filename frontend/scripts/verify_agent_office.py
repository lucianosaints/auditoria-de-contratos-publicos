"""QA somente leitura; prévia não pode enviar ações ao executor."""
import site
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors, writes = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: writes.append(r.url) if r.method != 'GET' else None)
    page.goto('http://127.0.0.1:4173')
    office = page.get_by_role('region', name='Escritório 2D dos agentes')
    office.wait_for()
    page.wait_for_timeout(4000)
    page.get_by_role('button', name='Ver prévia do fluxo').click()
    page.wait_for_timeout(3500)
    assert 'PRÉVIA ANIMADA' in office.inner_text()
    walker = office.locator('.office-walker')
    assert walker.count() == 1
    assert walker.locator('.office-held-document').count() == 1
    first_position = walker.locator('.office-person').get_attribute('transform')
    page.wait_for_timeout(300)
    assert walker.locator('.office-person').get_attribute('transform') != first_position
    page.get_by_role('button', name='Pausar animação').click()
    assert 'pausada' in office.inner_text()
    stopped_position = walker.locator('.office-person').get_attribute('transform')
    page.wait_for_timeout(300)
    assert walker.locator('.office-person').get_attribute('transform') == stopped_position
    page.get_by_role('button', name='Revisor', exact=True).click()
    assert 'Questiona achados' in office.inner_text()
    out = ROOT / 'frontend/qa'
    out.mkdir(exist_ok=True)
    office.screenshot(path=str(out / 'agent-office-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(out / 'agent-office-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Voltar ao estado real').click()
    assert 'PRÉVIA ANIMADA' not in office.inner_text()
    assert not errors, errors
    assert not writes, writes
    browser.close()
    print('Desktop/mobile aprovados; zero erros JS, overflow ou ações enviadas.')
