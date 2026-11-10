"""Ensaio isolado de UM anexo da linha 109; sem IA, .env ou banco."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.documents import DocumentSettings, collect_documents, document_sources


def main():
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
    names = ('contratos.json', 'parecer.json', 'relatorio.md')
    before = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    folder = ROOT / 'data/raw' / ('document_verificacao_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    folder.mkdir(parents=True)
    audit = SimpleNamespace(suspeitos=[SimpleNamespace(linha=109)])
    result = collect_documents(folder, records, audit, DocumentSettings(max_links=1, max_documents=1, max_pages=10))
    docs = [d for e in result['consultas'] for d in e['documentos']]
    sources, coverage = document_sources(result, 109, records[108])
    proof = {'pasta': str(folder), 'status': result['status'],
        'documentos': [{'status': d['status'], 'paginas': len(d['paginas']), 'erro': d.get('erro'),
                       'caracteres': sum(len(p['texto']) for p in d['paginas']),
                       'ocr_paginas': sum(p['metodo'] == 'ocr_windows' for p in d['paginas'])} for d in docs],
        'fontes_para_agentes': len(sources), 'cobertura': coverage,
        'original_preservado': before == {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}}
    (folder / 'verificacao.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(proof, ensure_ascii=False), flush=True)
    return 0 if docs and all(d['status'] in {'lido', 'parcial'} for d in docs) and proof['original_preservado'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
