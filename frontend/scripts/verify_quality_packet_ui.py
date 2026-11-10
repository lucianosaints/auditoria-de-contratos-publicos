"""QA do caderno real sem decisões e de formulário/exportação com casos fictícios."""
import json
import site
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from playwright.sync_api import sync_playwright, expect
from src.quality_packet import build_packet
from src.quality_evaluation import evaluate, make_sample

OUT = ROOT / 'frontend/qa'
REAL = ROOT / 'data/avaliacao_humana_caderno_20261021'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: external.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
    page.goto((REAL / 'avaliar.html').as_uri(), wait_until='load')
    expect(page.locator('.case')).to_have_count(40)
    expect(page.locator('#progress')).to_contain_text('40 pendentes')
    with page.expect_download() as download:
        page.get_by_role('button', name='Exportar referência preenchida', exact=True).click()
    downloaded = OUT / 'quality-reference-pending.json'
    download.value.save_as(downloaded)
    assert json.loads(downloaded.read_text(encoding='utf-8')) == json.loads((REAL / 'referencia_base.json').read_text(encoding='utf-8'))
    page.screenshot(path=str(OUT / 'quality-packet-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('.case').first.locator('summary').first.click()
    page.screenshot(path=str(OUT / 'quality-packet-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    # Formulário preenchido apenas em conjunto explicitamente fictício de QA.
    with tempfile.TemporaryDirectory(dir=ROOT / 'data/test_runtime') as tmp:
        root = Path(tmp); source = root / 'source'; source.mkdir()
        records = [{'Objeto': '</script><img src=x onerror="window.__packetXss=1">', 'Detalhe - Número': '1 - 2026'}, {'Objeto': 'Outro caso fictício'}]
        audit = {'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Motivo de teste'}], 'linhas_analisadas': [1, 2]}
        reference = make_sample(records, audit, 1)
        for name, data in [('contratos.json', records), ('parecer.json', audit)]:
            (source / name).write_text(json.dumps(data), encoding='utf-8')
        ref = root / 'reference.json'; ref.write_text(json.dumps(reference), encoding='utf-8')
        build_packet(source, ref, root / 'packet')
        page.goto((root / 'packet/avaliar.html').as_uri(), wait_until='load')
        page.locator('.case').first.locator('summary').first.click()
        assert page.evaluate('window.__packetXss') is None
        page.get_by_label('Decisão da linha 1', exact=True).select_option('true')
        page.get_by_role('button', name='Exportar referência preenchida', exact=True).click()
        expect(page.locator('#message')).to_contain_text('Linha 1: decisão exige')
        page.get_by_label('Responsável pela avaliação da linha 1', exact=True).fill('Pessoa fictícia de QA')
        page.get_by_label('Justificativa e limites da linha 1', exact=True).fill('Resposta fictícia para testar exportação.')
        page.get_by_label('Fontes conferidas — uma por linha, incluindo página quando aplicável da linha 1', exact=True).fill('Fonte fictícia, página 1')
        page.reload(wait_until='load')
        page.locator('.case').first.locator('summary').first.click()
        expect(page.get_by_label('Decisão da linha 1', exact=True)).to_have_value('true')
        with page.expect_download() as exported:
            page.get_by_role('button', name='Exportar referência preenchida', exact=True).click()
        fixture_path = OUT / 'quality-reference-fixture.json'
        exported.value.save_as(fixture_path)
        filled = json.loads(fixture_path.read_text(encoding='utf-8'))
        assert evaluate(records, audit, filled)['avaliados'] == 1
        assert filled['itens'][1]['exige_diligencia'] is None
        assert filled['coleta_sha256'] == reference['coleta_sha256']
        page.get_by_role('button', name='Mostrar só pendentes', exact=True).click()
        expect(page.locator('.case:visible')).to_have_count(1)
    assert not errors, errors
    assert not external, external
    (OUT / 'quality-packet-verificacao.json').write_text(json.dumps({'casos_reais': 40, 'decisoes_reais': 0,
        'formulario_exportacao_e_persistencia': 'conjunto_ficticio_de_QA', 'erros_js': errors, 'requisicoes_externas': external,
        'mobile_sem_overflow': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print('Caderno aprovado: 40 casos pendentes, exportação validada em fixture, sem rede ou erros JS.')
