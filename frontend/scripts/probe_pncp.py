"""Consulta pública de cobertura; só envia CNPJ do Município e intervalo público."""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/raw/pncp_verificacao_20261021'


def get(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read(10 * 1024 * 1024))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    schema = get('https://pncp.gov.br/api/consulta/v3/api-docs')
    (OUT / 'consulta_schema.json').write_text(json.dumps(schema, ensure_ascii=False), encoding='utf-8')
    page = get('https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20260101&dataFinal=20261021&cnpjOrgao=29131075000193&pagina=1&tamanhoPagina=500')
    (OUT / 'contratos_pagina_1.json').write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in page.items() if k != 'data'}, ensure_ascii=True))
    print(json.dumps(page.get('data', [])[:1], ensure_ascii=True, indent=2))
