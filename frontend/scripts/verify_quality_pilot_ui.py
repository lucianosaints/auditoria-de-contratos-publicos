"""QA real somente leitura; preenchimento, tempos e retomada apenas em casos fictícios."""
import copy
import hashlib
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
from src.quality_evaluation import make_sample, evaluate

OUT = ROOT / 'frontend/qa'
REAL = ROOT / 'data/piloto_supervisionado_20261023'
SOURCE = ROOT / 'data/reports/20261020T015002Z_72b23869'
NAMES = ['contratos.json', 'parecer.json', 'documentos.json', 'pncp.json', 'financeiro.json',
         'relatorio.md', 'revisao_agentes.json', 'indicadores.json', 'arquivamento.json']
hashes = lambda: {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in NAMES}
before = hashes()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1100}, accept_downloads=True)
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: external.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
    page.goto((REAL / 'avaliar.html').as_uri(), wait_until='load')
    expect(page.locator('.case')).to_have_count(40)
    expect(page.locator('.system-review')).to_have_count(0)
    expect(page.locator('#progress')).to_contain_text('40 decisões pendentes')
    with page.expect_download() as download:
        page.get_by_role('button', name='Exportar progresso do piloto', exact=True).click()
    pending_path = OUT / 'pilot-reference-pending.json'
    download.value.save_as(pending_path)
    pending = json.loads(pending_path.read_text(encoding='utf-8'))
    assert pending == json.loads((REAL / 'referencia_base.json').read_text(encoding='utf-8'))
    assert evaluate(json.loads((SOURCE / 'contratos.json').read_text(encoding='utf-8')),
                    json.loads((SOURCE / 'parecer.json').read_text(encoding='utf-8')), pending)['avaliados'] == 0
    page.screenshot(path=str(OUT / 'quality-pilot-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('.case').first.locator('summary').first.click()
    page.screenshot(path=str(OUT / 'quality-pilot-mobile.png'), full_page=False)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    # Identificação, decisões e cronômetros a seguir pertencem somente à fixture.
    with tempfile.TemporaryDirectory(dir=ROOT / 'data/test_runtime') as temporary:
        root = Path(temporary); folder = root / 'source'; folder.mkdir()
        records = [{'Objeto': '</script><img src=x onerror="window.__pilotXss=1">',
                    'Detalhe - Número': '1 - 2026'}, {'Objeto': 'Outro caso fictício'}]
        audit = {'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Alerta fictício para QA'}]}
        for name, value in [('contratos.json', records), ('parecer.json', audit)]:
            (folder / name).write_text(json.dumps(value), encoding='utf-8')
        reference = make_sample(records, audit, 1)
        ref = root / 'reference.json'; ref.write_text(json.dumps(reference), encoding='utf-8')
        build_packet(folder, ref, root / 'pilot', pilot=True)
        uri = (root / 'pilot/avaliar.html').as_uri()
        page.goto(uri, wait_until='load')
        assert page.evaluate('window.__pilotXss') is None
        page.get_by_label('Seu nome ou identificação profissional').fill('Pessoa fictícia de QA')
        card = page.locator('.case[data-line="1"]')
        card.locator('summary').first.click()
        expect(card.locator('.system-review')).to_have_count(0)
        page.get_by_label('Decisão independente da linha 1', exact=True).select_option('true')
        page.get_by_label('Justificativa e limites da linha 1', exact=True).fill('Fundamento fictício conferido.')
        page.get_by_label('Fontes conferidas da linha 1 — uma por linha, com página', exact=True).fill('Fonte fictícia p. 1')
        card.get_by_role('button', name='Encerrar conferência independente', exact=True).click()
        expect(page.locator('#message')).to_contain_text('registre o tempo')
        card.get_by_role('button', name='Iniciar / retomar conferência', exact=True).click()
        page.wait_for_timeout(180)
        card.get_by_role('button', name='Encerrar conferência independente', exact=True).click()
        expect(page.get_by_label('Decisão independente da linha 1', exact=True)).to_be_disabled()
        card.get_by_role('button', name='Consultar triagem e iniciar tempo', exact=True).click()
        expect(card.locator('.system-review')).to_contain_text('Alerta fictício')
        page.wait_for_timeout(150)
        card.get_by_role('button', name='Pausar consulta', exact=True).click()
        page.get_by_label('Reavaliação assistida da linha 1', exact=True).select_option('false')
        page.get_by_label('O que o sistema ajudou ou deixou de esclarecer na linha 1', exact=True).fill('Reavaliação fictícia; decisão inicial preservada.')
        # Uma referência com exposição prévia fica fora das métricas de acerto.
        card2 = page.locator('.case[data-line="2"]');card2.locator('summary').first.click()
        page.get_by_label('Já conhecia a triagem da linha 2', exact=True).check()
        page.get_by_label('Decisão independente da linha 2', exact=True).select_option('false')
        page.get_by_label('Justificativa e limites da linha 2', exact=True).fill('Já conhecia a triagem fictícia.')
        page.get_by_label('Fontes conferidas da linha 2 — uma por linha, com página', exact=True).fill('Fonte fictícia p. 2')
        card2.get_by_role('button', name='Iniciar / retomar conferência', exact=True).click()
        page.wait_for_timeout(100)
        card2.get_by_role('button', name='Encerrar conferência independente', exact=True).click()
        with page.expect_download() as download:
            page.get_by_role('button', name='Exportar progresso do piloto', exact=True).click()
        filled_path = OUT / 'pilot-reference-fixture.json'; download.value.save_as(filled_path)
        filled = json.loads(filled_path.read_text(encoding='utf-8'))
        result = evaluate(records, audit, filled)
        assert result['avaliados'] == 1 and result['verdadeiros_positivos'] == 1
        assert result['piloto']['linhas_nao_elegiveis_para_metricas'] == [2]
        assert result['piloto']['conferencia_independente']['total_segundos'] > 0
        assert filled['itens'][0]['exige_diligencia'] is True
        assert filled['piloto']['itens'][0]['reavaliacao_assistida']['exige_diligencia'] is False
        assert result['piloto']['tempo_economizado_segundos'] is None
        page.reload(wait_until='load')
        expect(page.locator('#active-clock')).to_contain_text('Nenhum cronômetro')
        expect(page.locator('#progress')).to_contain_text('2/2 conferências')
        # Retomada de exportação e recusa de fonte incompatível sem perder o rascunho.
        page.evaluate('localStorage.clear()');page.reload(wait_until='load')
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('#file').set_input_files(str(filled_path))
        expect(page.locator('#message')).to_contain_text('Progresso importado')
        bad = copy.deepcopy(filled);bad['coleta_sha256'] = 'outra coleta'
        bad_path = root / 'incompatible.json';bad_path.write_text(json.dumps(bad), encoding='utf-8')
        page.locator('#file').set_input_files(str(bad_path))
        expect(page.locator('#message')).to_contain_text('incompatível')
        expect(page.locator('#progress')).to_contain_text('2/2 conferências')
        page.locator('.case').first.locator('summary').first.click()
        page.screenshot(path=str(OUT / 'quality-pilot-fixture-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    assert not external, external
    assert before == hashes()
    (OUT / 'quality-pilot-verificacao.json').write_text(json.dumps({'casos_reais': 40, 'decisoes_reais': 0,
        'medicoes_e_decisoes': 'somente_fixture_ficticia', 'primeira_decisao_preservada': True,
        'exposicao_previa_excluida': True, 'retomada_por_importacao': True, 'cronometros_pausados_ao_recarregar': True,
        'nove_artefatos_preservados': True, 'erros_js': errors, 'requisicoes_externas': external,
        'mobile_sem_overflow': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print('Piloto: 40 casos pendentes; fluxo, tempos e importação testados somente em fixture, sem rede.')
