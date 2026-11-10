"""Valida reconciliação real autorizada, preservando os artefatos da auditoria."""
import argparse
import hashlib
import json
import os
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
os.environ.setdefault('PYTHONUTF8', '1')
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['CREWAI_STORAGE_DIR'] = str(ROOT / 'data/test_runtime/pncp')
os.environ['LOCALAPPDATA'] = str(ROOT / 'data/test_runtime')

from src.atomic_files import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true', help='Consultar apenas API pública PNCP, sem IA ou banco')
    args = parser.parse_args()
    run = '20261020T015002Z_72b23869'
    folder = ROOT / 'data/reports' / run
    names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'arquivamento.json',
             'documentos.json', 'verificacao_evidencias.json']
    hashes = lambda: {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in names}
    before = hashes()
    if args.real:
        from src.ui_jobs import execute_action
        code, summary = execute_action('consultar_pncp', run)
    else:
        code, summary = 0, {'rede': 'não consultada; arquivos salvos'}
    result = json.loads((folder / 'pncp.json').read_text(encoding='utf-8'))
    from collections import Counter
    from src.audit_models import ParecerAuditoria
    from src.documents import plan_documents
    records = json.loads((folder / 'contratos.json').read_text(encoding='utf-8'))
    audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
    plan = plan_documents(records, audit, pncp=result)
    proof = {'execucao': run, 'resultado': summary, 'catalogo': result['catalogo'],
             'situacoes': dict(Counter(e['situacao'] for e in result['consultas'])),
             'documentos_pncp': sum(len(e['documentos']) for e in result['consultas']),
             'planejamento_documental': {k: v for k, v in plan.items() if k != 'consultas'},
             'chamadas_ia': 0, 'chamadas_banco': 0, 'originais_preservados': before == hashes(),
             'hashes_preservados': before}
    assert proof['originais_preservados']
    write_json(ROOT / 'data/raw/pncp_verificacao_20261021/verificacao.json', proof)
    print(json.dumps(proof, ensure_ascii=True, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
