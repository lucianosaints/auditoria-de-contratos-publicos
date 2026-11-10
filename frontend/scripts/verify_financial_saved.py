"""Executa a consulta financeira limitada na execução principal e confere preservação."""
import contextlib
import hashlib
import json
import os
import site
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
os.environ['LOCALAPPDATA'] = str(ROOT / 'data/test_runtime')
os.environ['CREWAI_STORAGE_DIR'] = str(ROOT / 'data/test_runtime')
os.environ['OTEL_SDK_DISABLED'] = 'true'
from src.ui_jobs import run_job, write_json, now

RUN = '20261020T015002Z_72b23869'
source = ROOT / 'data/reports' / RUN
names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'documentos.json', 'pncp.json', 'indicadores.json', 'arquivamento.json']
hashes = lambda: {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in names}
before = hashes()
jobs = ROOT / 'data/ui_jobs'
job_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + uuid.uuid4().hex[:8]
write_json(jobs / (job_id + '.json'), {'id': job_id, 'action': 'consultar_financeiro', 'run_id': RUN,
    'status': 'iniciando', 'created_at': now(), 'pid': None})
print('Job financeiro:', job_id, flush=True)
with (jobs / (job_id + '.log')).open('w', encoding='utf-8') as stream:
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        code = run_job(job_id)
after = hashes()
receipt = {'job_id': job_id, 'exit_code': code, 'originais_preservados': before == after,
           'antes': before, 'depois': after,
           'resultado': json.loads((jobs / (job_id + '.json')).read_text(encoding='utf-8'))}
latest = ROOT / 'data/raw/financial_integration_20261021/execucao_principal.json'
if latest.exists():
    previous = json.loads(latest.read_text(encoding='utf-8'))
    write_json(latest.parent / 'recibos' / (previous['job_id'] + '.json'), previous)
write_json(latest.parent / 'recibos' / (job_id + '.json'), receipt)
write_json(latest, receipt)
print(json.dumps({k: v for k, v in receipt.items() if k not in ('antes', 'depois')}, ensure_ascii=True))
assert before == after
raise SystemExit(code)
