"""Consulta isolada de duas identidades já selecionadas; sem IA/banco/auditoria nova."""
import hashlib
import json
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from src.financial import FinancialClient, FinancialSettings, check_detail, write_json

source = ROOT / 'data/reports/20261020T015002Z_72b23869'
out = ROOT / 'data/raw/financial_two_cases_20261021'
records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
financial = json.loads((source / 'financeiro.json').read_text(encoding='utf-8'))
client = FinancialClient(out, FinancialSettings(max_suppliers=2, max_details=2))
names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'documentos.json', 'pncp.json', 'indicadores.json', 'arquivamento.json']
hashes = lambda: {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
before = hashes()
result = []
try:
    for line, expected in [(96, [5342, 2026]), (175, [4003, 2026])]:
        record = records[line - 1]
        entry = next(e for e in financial['consultas'] if e['linha'] == line)
        link = next(v for v in entry['vinculos'] if v['numero_ano_esperado'] == expected)
        rows, listing_source = client.listing(entry['filtros']['cnpj'], expected[1])
        candidates = [r for r in rows if r['Empenho'] == f'{expected[0]}/{expected[1]}']
        detail, detail_source = client.detail(link['url'])
        assessed = check_detail(expected, detail, record, candidates[0] if len(candidates) == 1 else None)
        result.append({'linha': line, 'cnpj': entry['filtros']['cnpj'], 'url_detalhe': link['url'],
                       'registros_no_filtro': len(rows), 'empenho_localizado_na_consulta': len(candidates),
                       'fonte_consulta': {k: v for k, v in listing_source.items() if k != 'html'},
                       'fonte_detalhe': {k: v for k, v in detail_source.items() if k != 'html'},
                       'resultado': assessed})
finally:
    client.close()
receipt = {'casos': result, 'originais_preservados': before == hashes(), 'antes': before, 'depois': hashes()}
write_json(out / 'verificacao.json', receipt)
print(json.dumps({'originais_preservados': receipt['originais_preservados'], 'casos': result}, ensure_ascii=True))
assert receipt['originais_preservados']
