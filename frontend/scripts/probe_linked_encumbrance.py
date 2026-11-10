"""Valida uma URL de empenho publicada no detalhe do contrato já salvo."""
import json
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from bs4 import BeautifulSoup
import requests

if __name__ == '__main__':
    folder = ROOT / 'data/reports/20261020T015002Z_72b23869'
    records = json.loads((folder / 'contratos.json').read_text(encoding='utf-8'))
    record = records[7]
    soup = BeautifulSoup((folder / record['Arquivo HTML dos detalhes']).read_text(encoding='utf-8'), 'html.parser')
    label = next(e for e in soup.select('.width-100') if e.get_text(' ', strip=True).rstrip(':') == 'Empenhos')
    url = label.find_next_sibling().select_one('a[href]')['href']
    assert url.startswith('https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao/') and url.endswith('/empenho')
    response = requests.get(url, timeout=(10, 50)); response.raise_for_status()
    out = ROOT / 'data/raw/financeiro_verificacao_20261021'
    (out / 'empenho_vinculado.html').write_text(response.text, encoding='utf-8')
    parsed = BeautifulSoup(response.text, 'html.parser')
    content = parsed.select_one('.content')
    print(content.get_text(' ', strip=True)[:14000].encode('ascii', errors='backslashreplace').decode())
    print(json.dumps([{'label':e.get_text(' ', strip=True),'value':e.find_next_sibling().get_text(' ',strip=True)[:2000] if e.find_next_sibling() else None}
                      for e in content.select('.width-100')],ensure_ascii=True,indent=2))
