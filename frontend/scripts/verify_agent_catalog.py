"""Verifica checkpoints anteriores; --real testa somente o segundo lote isolado.

Sem --real não chama IA/rede/banco. Não publica resultados na execução original.
"""
import argparse
import hashlib
import json
import logging
import os
import shutil
import site
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
os.environ.setdefault('CREWAI_STORAGE_DIR', str(ROOT / 'data/test_runtime'))
os.environ.setdefault('OTEL_SDK_DISABLED', 'true')

from src.agent_review import ReviewSettings, build_dossiers, read_gazette, review_saved_audit, split_dossiers
from src.audit_models import ParecerAuditoria
from src.batch_pipeline import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    originals = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json',
                 'agentes/0001/investigacao.json', 'agentes/0001/revisao.json']
    before = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in originals}
    records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
    audit = ParecerAuditoria.model_validate_json((source / 'parecer.json').read_text(encoding='utf-8'))
    gazette = read_gazette(source)
    batches = split_dossiers(build_dossiers(records, audit, gazette), ReviewSettings())
    root = ROOT / 'data/raw' / ('agent_catalogo_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir(parents=True)

    def prepare(folder, selected):
        folder.mkdir(parents=True)
        lines = {d['linha'] for d in selected}
        sample = audit.model_copy(deep=True)
        sample.suspeitos = [f for f in sample.suspeitos if f.linha in lines]
        sample.relatorio_markdown = '# Ensaio isolado do catálogo de citações'
        write_json(folder / 'parecer.json', sample.model_dump())
        if gazette:
            write_json(folder / 'diario_oficial.json', {**gazette, 'consultas': [q for q in gazette['consultas'] if q['linha'] in lines]})
        return sample

    cached = root / 'retomada'
    first_audit = prepare(cached, batches[0])
    (cached / 'agentes/0001').mkdir(parents=True)
    for name in ('investigacao.json', 'revisao.json'):
        shutil.copyfile(source / 'agentes/0001' / name, cached / 'agentes/0001' / name)
    def forbidden(*args, **kwargs):
        raise AssertionError('Checkpoints completos não devem chamar IA nem esperar.')
    resumed = review_saved_audit(SimpleNamespace(model='gemini-3.5-flash-lite'), cached, records, first_audit,
                                worker=forbidden, wait=forbidden)
    proof = {'retomada_primeiro_lote': {'status': resumed['status'], 'contratos': len(resumed['itens']),
             'etapas_recuperadas': resumed['etapas_recuperadas'], 'etapas_migradas': resumed['etapas_migradas'],
             'chamadas_IA': resumed['chamadas_nesta_execucao']}}
    assert resumed['status'] == 'concluida' and resumed['etapas_recuperadas'] == 2 and resumed['chamadas_nesta_execucao'] == 0
    if args.real:
        from dotenv import load_dotenv
        from src.main import create_audit_llm
        load_dotenv(ROOT / '.env', override=False)
        selected = batches[1]
        live = root / 'lote_2_real'
        sample = prepare(live, selected)
        print('Ensaio real isolado do lote 2: linhas ' + ', '.join(str(d['linha']) for d in selected), flush=True)
        result = review_saved_audit(create_audit_llm(), live, records, sample, ReviewSettings(quota_retries=0))
        proof['lote_2_real'] = {'status': result['status'], 'contratos': len(result['itens']),
            'linhas': [d['linha'] for d in selected], 'chamadas_IA': result['chamadas_nesta_execucao'],
            'erro': result.get('erro')}
    proof['originais_preservados'] = before == {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in originals}
    write_json(root / 'verificacao.json', proof)
    print(json.dumps({'pasta': str(root.relative_to(ROOT)), **proof}, ensure_ascii=False), flush=True)
    return 0 if proof['originais_preservados'] and (not args.real or proof['lote_2_real']['status'] == 'concluida') else 1


if __name__ == '__main__': raise SystemExit(main())
