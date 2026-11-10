"""Consulta detalhe financeiro público previamente observado no HTML do portal."""
import json
import site
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from bs4 import BeautifulSoup
import requests

if __name__ == '__main__':
    out = ROOT / 'data/raw/financeiro_verificacao_20261021'
    entries = json.loads((out / 'candidatos_locais.json').read_text(encoding='utf-8'))
    url = entries[0]['url']
    assert urlsplit(url).hostname == 'transparencia.marica.rj.gov.br'
    r = requests.get(url, timeout=(10, 50)); r.raise_for_status()
    (out / 'detalhe.html').write_text(r.text, encoding='utf-8')
    soup = BeautifulSoup(r.text, 'html.parser')
    content = soup.select_one('.content') or soup
    print(content.get_text(' ', strip=True)[:16000].encode('ascii', errors='backslashreplace').decode())
    print(json.dumps([{'text': a.get_text(' ', strip=True), 'url': a.get('href'), 'data': a.get('data-href')}
                      for a in content.select('a[href],a[data-href]')], ensure_ascii=True)[:5000])
