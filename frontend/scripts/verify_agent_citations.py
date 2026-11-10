"""Reproduz o primeiro lote REAL com respostas simuladas; sem IA/rede/banco."""
import hashlib
import json
import os
import site
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
os.environ.setdefault('CREWAI_STORAGE_DIR', str(ROOT / 'data/test_runtime'))
os.environ.setdefault('OTEL_SDK_DISABLED', 'true')

from src.agent_review import ReviewSettings, build_dossiers, read_gazette, review_saved_audit, split_dossiers, validate_stage, parse_stage_response
from src.audit_models import ParecerAuditoria
from src.batch_pipeline import write_json


def main():
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    names = ('contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json')
    before = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
    audit = ParecerAuditoria.model_validate_json((source / 'parecer.json').read_text(encoding='utf-8'))
    settings = ReviewSettings(interval_seconds=0)
    gazette = read_gazette(source)
    first = split_dossiers(build_dossiers(records, audit, gazette, settings), settings)[0]
    lines = {d['linha'] for d in first}
    audit = audit.model_copy(deep=True)
    audit.suspeitos = [f for f in audit.suspeitos if f.linha in lines]
    audit.relatorio_markdown = '# Ensaio local com respostas simuladas\nSem validação semântica de achados.'
    folder = ROOT / 'data/raw' / ('agent_citacoes_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    folder.mkdir(parents=True)
    write_json(folder / 'parecer.json', audit.model_dump())
    if gazette:
        gazette = {**gazette, 'consultas': [q for q in gazette['consultas'] if q['linha'] in lines]}
        write_json(folder / 'diario_oficial.json', gazette)
    replayed = []
    for path in (source / 'agentes/0001/rejeicoes').glob('*.json'):
        rejected = json.loads(path.read_text(encoding='utf-8'))
        if not rejected.get('resposta_original'):
            continue
        try:
            validate_stage('investigacao', parse_stage_response(rejected['resposta_original']), first)
        except ValueError:
            replayed.append(path.name)

    def worker(llm, stage, batch, skills, previous, feedback):
        items = []
        for dossier in batch:
            source = next((s for s in dossier['fontes'] if s['tipo'] == 'campo_portal' and 'valor' in s['rotulo'].lower()), dossier['fontes'][0])
            pair = {'fonte_id': source['id'], 'trecho': source['texto'][:700]}
            common = {'linha': dossier['linha'], 'limite': 'Resposta simulada para testar a validação, sem concluir sobre o contrato.', 'evidencias': [pair]}
            if stage == 'investigacao':
                items.append({**common, 'observacao': 'Conferência literal de campo monetário no ensaio local.'})
            else:
                common['evidencias'] = next(i['evidencias'] for i in previous['itens'] if i['linha'] == dossier['linha'])
                items.append({**common, 'situacao': 'necessita_documentos', 'explicacao_simples': 'Resultado demonstrativo do teste, sem análise substantiva.',
                              'proxima_diligencia': 'Conferir o processo administrativo antes de concluir.'})
        return json.dumps({'itens': items}, ensure_ascii=False)

    result = review_saved_audit(None, folder, records, audit, settings, worker=worker)
    proof = {'modo': 'respostas_simuladas_sem_IA_rede_banco', 'linhas': sorted(lines), 'status': result['status'],
        'contratos': len(result['itens']), 'etapas_simuladas': result['chamadas_nesta_execucao'],
        'citacoes': [e['trecho'] for i in result['itens'] for e in i['evidencias']],
        'respostas_antigas_invalidas_continuam_rejeitadas': replayed,
        'originais_preservados': before == {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}}
    write_json(folder / 'verificacao.json', proof)
    assert result['status'] == 'concluida' and len(result['itens']) == len(lines) and proof['originais_preservados']
    print(json.dumps({'pasta': str(folder.relative_to(ROOT)), **proof}, ensure_ascii=False))


if __name__ == '__main__': main()
