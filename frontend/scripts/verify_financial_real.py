"""Amostra financeira real isolada: um contrato, um CNPJ/exercício, dois detalhes."""
import hashlib
import json
import shutil
import site
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
from src.financial import FinancialSettings, collect_financial, write_json

source = ROOT / 'data/reports/20261020T015002Z_72b23869'
folder = ROOT / 'data/raw/financial_integration_20261021'
folder.mkdir(parents=True, exist_ok=True)
names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'documentos.json', 'pncp.json', 'indicadores.json', 'arquivamento.json']
hashes = lambda: {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in names}
before = hashes()
record = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))[4]
filename = record['Arquivo HTML dos detalhes']
target = (folder / filename).resolve()
assert target.is_relative_to(folder.resolve())
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(source / filename, target)
write_json(folder / 'contratos.json', [record])
write_json(folder / 'parecer.json', {'linhas_analisadas': [1], 'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Amostra financeira isolada'}], 'relatorio_markdown': 'Amostra isolada'})
result = collect_financial(folder, [record], SimpleNamespace(suspeitos=[SimpleNamespace(linha=1)]),
                           FinancialSettings(max_suppliers=1, max_details=2))
receipt = {'originais_preservados': before == hashes(), 'antes': before, 'depois': hashes(),
           'consultas': result['consultas_fornecedores'], 'status': result['status'],
           'vinculos': [{k: v for k, v in link.items() if k != 'detalhe'} for link in result['consultas'][0]['vinculos']]}
write_json(folder / 'verificacao.json', receipt)
print(json.dumps(receipt, ensure_ascii=True))
assert receipt['originais_preservados']
