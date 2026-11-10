"""Inspeção pública de estrutura do portal; nenhum dado local enviado."""
import json
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from bs4 import BeautifulSoup
import requests

if __name__ == '__main__':
    out = ROOT / 'data/raw/financeiro_verificacao_20261021'
    out.mkdir(parents=True, exist_ok=True)
    session = requests.Session(); session.trust_env = False
    url = 'https://transparencia.marica.rj.gov.br/e-cidade/consulta-empenhos'
    response = session.get(url, timeout=(10, 50)); response.raise_for_status()
    (out / 'portal.html').write_text(response.text, encoding='utf-8')
    soup = BeautifulSoup(response.text, 'html.parser')
    info = {'forms': [{'action': f.get('action'), 'method': f.get('method'),
                       'fields': [{'tag': i.name, 'name': i.get('name'), 'id': i.get('id'),
                                   'type': i.get('type'), 'value': i.get('value') if i.get('name') != '_token' else '[oculto]',
                                   'options': [o.get('value') for o in i.select('option')][:30]} for i in f.select('input,select')]}
                      for f in soup.select('form')],
            'tables': [t.get_text(' ', strip=True)[:1800] for t in soup.select('table')],
            'links': [{'text': a.get_text(' ', strip=True), 'url': a.get('href'), 'data': a.get('data-href')}
                      for a in soup.select('a[href],a[data-href]') if any(s in str(a).lower() for s in ('empenho', 'detalh', 'csv', 'excel', 'próxim'))][-35:],
            'scripts': [s.get('src') or s.get_text()[-9000:] for s in soup.select('script')][-10:]}
    (out / 'estrutura.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=True, indent=2))
