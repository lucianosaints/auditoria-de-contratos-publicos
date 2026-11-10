"""Baixa PDFs confirmados no PNCP e reaproveita originais locais; sem IA/banco."""
import hashlib
import json
import os
import site
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['CREWAI_STORAGE_DIR'] = str(ROOT / 'data/test_runtime/pncp-documents')
os.environ['LOCALAPPDATA'] = str(ROOT / 'data/test_runtime')


def main():
    from src.atomic_files import write_json
    from src.batch_pipeline import execution_lock, load_records
    from src.audit_models import ParecerAuditoria
    from src.documents import collect_documents, DocumentSettings
    from src.rag import build_index
    folder = ROOT / 'data/reports/20261020T015002Z_72b23869'
    out = ROOT / 'data/raw/pncp_verificacao_20261021'
    names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json',
             'arquivamento.json', 'verificacao_evidencias.json']
    hashes = lambda: {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in names}
    before = hashes()
    old_pdf_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder / 'documentos').glob('*.pdf')}
    with execution_lock(folder):
        records = load_records(folder)
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        result = collect_documents(folder, records, audit, DocumentSettings(max_documents=300))
        pncp_docs = {d['id']: d for e in result['consultas'] for d in e['documentos'] if d.get('origem') == 'pncp'}
        existing_index = folder / 'rag/indice.sqlite3'
        if existing_index.exists():
            data = existing_index.read_bytes()
            archived = folder / 'rag/historico' / f'{hashlib.sha256(data).hexdigest()}.sqlite3'
            archived.parent.mkdir(parents=True, exist_ok=True)
            if not archived.exists():
                archived.write_bytes(data)
        rag = build_index(folder)
        import pdfplumber
        examples = []
        for document in list(pncp_docs.values())[:2]:
            if not document.get('arquivo'):
                continue
            with pdfplumber.open(folder / document['arquivo']) as pdf:
                for number in sorted({0, len(pdf.pages) - 1}):
                    pdf.pages[number].to_image(resolution=100).original.save(out / f'amostra_{document["id"][:10]}_p{number+1}.png')
                examples.append({'id': document['id'], 'paginas': len(pdf.pages),
                                 'inicio': (pdf.pages[0].extract_text() or '')[:1400]})
    proof = {'documentos_unicos': len({d['id'] for e in result['consultas'] for d in e['documentos']}),
             'documentos_pncp': len(pncp_docs), 'status_pncp': dict(Counter(d['status'] for d in pncp_docs.values())),
             'tipos_pncp': dict(Counter(d.get('tipo_documento') for d in pncp_docs.values())),
             'paginas_pncp': sum(len(d['paginas']) for d in pncp_docs.values()),
             'documentos_status': result['status'], 'rag': rag, 'exemplos': examples,
             'artefatos_originais_preservados': before == hashes(),
             'pdfs_anteriores_preservados': old_pdf_hashes == {
                 name: hashlib.sha256((folder / 'documentos' / name).read_bytes()).hexdigest() for name in old_pdf_hashes},
             'chamadas_ia': 0, 'chamadas_banco': 0}
    assert proof['artefatos_originais_preservados'] and proof['pdfs_anteriores_preservados']
    write_json(out / 'verificacao_documentos.json', proof)
    print(json.dumps(proof, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
