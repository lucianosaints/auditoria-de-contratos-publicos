"""Amostra REAL opcional: dois agentes, um contrato salvo, sem banco/coleta.

Executar explicitamente; não faz parte de testes automatizados. Usa Gemini.
Artefatos ficam em data/raw/agent_verificacao_<UTC>/, fora da lista do painel.
"""
import json
import os
import site
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv' / 'Lib' / 'site-packages'))
# O diretório de QA mantém também os caches locais do CrewAI no workspace.
os.environ.setdefault('CREWAI_STORAGE_DIR', str(ROOT / 'data' / 'test_runtime'))
os.environ.setdefault('OTEL_SDK_DISABLED', 'true')

from dotenv import load_dotenv
from src.audit_models import ParecerAuditoria
from src.agent_review import review_saved_audit
from src.batch_pipeline import fingerprint, write_json
from src.main import create_audit_llm

load_dotenv(ROOT / '.env', override=False)
logging.basicConfig(level=logging.INFO)
source = ROOT / 'data' / 'reports' / '20261020T015002Z_72b23869'
before = {name: fingerprint((source / name).read_text(encoding='utf-8'))
          for name in ('contratos.json', 'parecer.json', 'relatorio.md')}
records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
audit = ParecerAuditoria.model_validate_json((source / 'parecer.json').read_text(encoding='utf-8'))
audit.suspeitos = [f for f in audit.suspeitos if f.linha == 109]
if not audit.suspeitos:
    raise RuntimeError('A amostra da linha 109 não está disponível; nenhuma chamada será feita.')
audit.relatorio_markdown = '# Amostra isolada de verificação dos agentes\n\nSomente a linha 109.'
folder = ROOT / 'data' / 'raw' / ('agent_verificacao_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
folder.mkdir(parents=True)
write_json(folder / 'parecer.json', audit.model_dump())
if (source / 'diario_oficial.json').exists():
    gazette = json.loads((source / 'diario_oficial.json').read_text(encoding='utf-8'))
    gazette['consultas'] = [q for q in gazette['consultas'] if q['linha'] == 109]
    write_json(folder / 'diario_oficial.json', gazette)
result = review_saved_audit(create_audit_llm(), folder, records, audit)
after = {name: fingerprint((source / name).read_text(encoding='utf-8')) for name in before}
verification = {'status': result['status'], 'contratos_revisados': len(result['itens']),
                'chamadas_de_etapas': result['chamadas_nesta_execucao'], 'original_preservado': before == after,
                'modelo': result['modelo'], 'pasta': str(folder.relative_to(ROOT))}
write_json(folder / 'verificacao.json', verification)
print(json.dumps(verification, ensure_ascii=False, indent=2))
if result['status'] != 'concluida' or before != after:
    raise SystemExit(1)
