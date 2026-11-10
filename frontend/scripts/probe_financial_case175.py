"""Inspeção isolada do empenho 4003/2026. --real consulta portal público, sem IA/banco."""
import argparse
import json
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true')
    parser.add_argument('--numero', choices=('4003', '140921'), default='4003')
    args = parser.parse_args()
    from bs4 import BeautifulSoup
    from src.financial import FinancialClient, FinancialSettings, SEARCH, HEADERS, digest, now
    from src.atomic_files import write_json
    folder = ROOT / 'data/raw/financial_case175_20261023'
    path = folder / f'consulta_numero_{args.numero}.json'
    if args.real:
        client = FinancialClient(folder, FinancialSettings(max_suppliers=1, max_details=3))
        try:
            initial = client.request(SEARCH)
            soup = BeautifulSoup(initial, 'html.parser')
            form = soup.select_one(f'form[action="{SEARCH}/pesquisar"]')
            token = form.select_one('[name="_token"]') if form else None
            if token is None or not token.get('value'):
                raise ValueError('Formulário/token público ausente.')
            payload = {'_token': token['value'], 'year': '2026', 'month': '', 'unit': '',
                       'beneficiary': '', 'document': '', 'encumbrance_number': args.numero}
            html = client.request(SEARCH + '/pesquisar', payload)
            write_json(path, {'url': SEARCH + '/pesquisar', 'filtros': {k: v for k, v in payload.items() if k != '_token'},
                             'consultado_em': now(), 'html': html, 'sha256': digest(html)})
        finally:
            client.close()
    if not path.exists():
        print('Sem evidência local. Use --real para consulta limitada.')
        return
    saved = json.loads(path.read_text(encoding='utf-8'))
    if saved['sha256'] != digest(saved['html']):
        raise ValueError('HTML salvo alterado.')
    soup = BeautifulSoup(saved['html'], 'html.parser')
    forms = [{e.get('name'): (e.select_one('option[selected]').get('value') if e.name == 'select' and e.select_one('option[selected]') else e.get('value', ''))
              for e in f.select('input[name],select[name]') if e.get('name') != '_token'} for f in soup.select('form')]
    tables = [t for t in soup.select('table') if [h.get_text(' ', strip=True) for h in t.select('thead th')] == HEADERS]
    rows = [[c.get_text(' ', strip=True) for c in r.select('td')] for t in tables for r in t.select('tbody tr')]
    links = [a['href'] for t in tables for a in t.select('tbody a[href]')]
    proof = {'filtros_devolvidos': forms, 'linhas': rows, 'links': links,
             'fonte': {k: v for k, v in saved.items() if k != 'html'}}
    write_json(folder / f'inspecao_numero_{args.numero}.json', proof)
    print(json.dumps(proof, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
