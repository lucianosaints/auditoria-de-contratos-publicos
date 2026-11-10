"""Retoma somente os dois PDFs PNCP grandes. --real usa rede pública, sem IA/banco."""
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
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['CREWAI_STORAGE_DIR'] = str(ROOT / 'data/test_runtime/large-pncp')
os.environ['LOCALAPPDATA'] = str(ROOT / 'data/test_runtime')
IDS = {'f15356ad669ddf1adad9d24c9aa1ff91f424a6dbae44d3e2c5dbb13733a161eb',
       'f37d6ccdf0d830190c51f2edddac1d4b6b26a07a61529cbbe039408f6517038a'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()
    from src.documents import collect_documents, DocumentSettings
    from src.atomic_files import write_json
    from src.audit_models import ParecerAuditoria
    from src.batch_pipeline import execution_lock, load_records
    from src.rag import build_index
    folder = ROOT / 'data/reports/20261020T015002Z_72b23869'
    output = ROOT / 'data/raw/large_pncp_20261023'
    names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json',
             'arquivamento.json', 'verificacao_evidencias.json', 'pncp.json',
             'indicadores.json', 'financeiro.json']
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    hashes = lambda: {name: sha(folder / name) for name in names}
    before = hashes()
    pdfs = {p.name: sha(p) for p in (folder / 'documentos').glob('*.pdf')}
    manifest = json.loads((folder / 'documentos.json').read_text(encoding='utf-8'))
    old_docs = {(e['linha'], d['id']): d for e in manifest['consultas'] for d in e['documentos']
                if d['id'] not in IDS}
    if not args.real:
        print(json.dumps({'ids': sorted(IDS), 'max_mb': 50, 'max_paginas': 30,
                          'rede_executada': False}, indent=2))
        return
    output.mkdir(parents=True, exist_ok=True)
    with execution_lock(folder):
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        result = collect_documents(folder, load_records(folder), audit,
            DocumentSettings(max_bytes=50 * 1024 * 1024), retry_ids=IDS)
        after_docs = {(e['linha'], d['id']): d for e in result['consultas'] for d in e['documentos']
                      if d['id'] not in IDS}
        selected = {d['id']: d for e in result['consultas'] for d in e['documentos'] if d['id'] in IDS}
        index = folder / 'rag/indice.sqlite3'
        if index.exists():
            archive = folder / 'rag/historico' / f'{sha(index)}.sqlite3'
            archive.parent.mkdir(parents=True, exist_ok=True)
            if not archive.exists():
                archive.write_bytes(index.read_bytes())
        rag = build_index(folder)
        proof = {'artefatos_inalterados': before == hashes(),
                 'documentos_nao_selecionados_inalterados': old_docs == after_docs,
                 'pdfs_anteriores_inalterados': all(sha(folder / 'documentos' / n) == h for n, h in pdfs.items()),
                 'documentos_processados': result['documentos_processados'],
                 'documentos_preservados': result['documentos_preservados'],
                 'limites_aplicados': result['limites_aplicados'], 'rag': rag,
                 'resultados': [{'id': d['id'], 'status': d['status'], 'erro': d.get('erro'),
                     'total_paginas': d.get('total_paginas'), 'paginas_extraidas': len(d['paginas']),
                     'avisos': d.get('avisos'), 'sha256': d.get('sha256'),
                     'bytes': (folder / d['arquivo']).stat().st_size if d.get('arquivo') else None}
                     for d in selected.values()], 'chamadas_ia': 0, 'chamadas_banco': 0}
        write_json(output / 'verificacao.json', proof)
        assert all(proof[k] for k in ('artefatos_inalterados', 'documentos_nao_selecionados_inalterados',
                                     'pdfs_anteriores_inalterados'))
    print(json.dumps(proof, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
