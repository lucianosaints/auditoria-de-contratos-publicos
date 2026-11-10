"""Três consultas alternativas explícitas, sem alterar a auditoria ou inferir vínculo."""
import argparse
import json
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))


def main():
    from bs4 import BeautifulSoup
    from src.financial import FinancialClient, FinancialSettings, SEARCH, HEADERS, digest, now
    from src.atomic_files import write_json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'data/raw/financial_alternative175_20261023/consultas'
    queries = [('nome_fornecedor', {'beneficiary': 'CS BRASIL'}),
               ('numero_com_ano', {'encumbrance_number': '4003/2026'}),
               ('unidade_numero', {'encumbrance_number': '4003'})]
    if args.real:
        client = FinancialClient(out, FinancialSettings())
        try:
            initial = client.request(SEARCH)
            soup = BeautifulSoup(initial, 'html.parser')
            form = soup.select_one(f'form[action="{SEARCH}/pesquisar"]')
            token = form.select_one('[name="_token"]') if form else None
            if token is None or not token.get('value'):
                raise ValueError('Formulário/token ausente.')
            units = [o for o in form.select('[name="unit"] option')
                     if o.get_text(' ', strip=True).upper() == 'SECRETARIA DE SEGURANÇA CIDADÃ']
            if len(units) != 1 or not units[0].get('value'):
                raise ValueError('Unidade orçamentária sem opção única no formulário.')
            queries[-1][1]['unit'] = units[0]['value']
            for name, extra in queries:
                payload = {'_token': token['value'], 'year': '2026', 'month': '', 'unit': '',
                           'beneficiary': '', 'document': '', 'encumbrance_number': '', **extra}
                html = client.request(SEARCH + '/pesquisar', payload)
                write_json(out / f'{name}.json', {'url': SEARCH + '/pesquisar', 'consultado_em': now(),
                    'filtros': {k: v for k, v in payload.items() if k != '_token'}, 'html': html, 'sha256': digest(html)})
        finally:
            client.close()
    results = []
    for name, _ in queries:
        saved = json.loads((out / f'{name}.json').read_text(encoding='utf-8'))
        if saved['sha256'] != digest(saved['html']):
            raise ValueError('Resposta salva alterada.')
        soup = BeautifulSoup(saved['html'], 'html.parser')
        form = soup.select_one(f'form[action="{SEARCH}/pesquisar"]')
        returned = {}
        for key, expected in saved['filtros'].items():
            element = form.select_one(f'[name="{key}"]') if form else None
            if element is None:
                raise ValueError('Filtro ausente: ' + key)
            option = element.select_one('option[selected]') if element.name == 'select' else None
            actual = option.get('value', '') if option else element.get('value', '')
            if actual != expected:
                raise ValueError('Filtro não confirmado: ' + key)
            returned[key] = actual
        tables = [t for t in soup.select('table') if [h.get_text(' ', strip=True) for h in t.select('thead th')] == HEADERS]
        if len(tables) != 1:
            raise ValueError('Tabela financeira com estrutura inesperada.')
        rows = []
        for row in tables[0].select('tbody tr'):
            cells = row.select('td')
            if len(cells) != len(HEADERS):
                raise ValueError('Linha financeira com estrutura inesperada.')
            rows.append(dict(zip(HEADERS, [c.get_text(' ', strip=True) for c in cells])))
        results.append({'consulta': name, 'filtros_conferidos': returned, 'registros': rows,
                        'fonte': {k: v for k, v in saved.items() if k != 'html'}})
    write_json(out / 'verificacao.json', results)
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
