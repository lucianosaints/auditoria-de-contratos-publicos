"""RAG + MCP real sobre PDF já baixado, em cópia temporária; zero IA/rede/banco."""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.rag import build_index
from src.rag_client import check_connection, retrieve_for_agents
from src.audit_models import ParecerAuditoria, Achado


def main():
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    sample = ROOT / 'data/raw/document_verificacao_20261020T235654Z'
    names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'arquivamento.json']
    before = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names if (source / n).exists()}
    records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='qa_rag_real_', dir=ROOT / 'data/reports') as name:
        folder = Path(name)
        shutil.copy2(source / 'contratos.json', folder / 'contratos.json')
        shutil.copy2(sample / 'documentos.json', folder / 'documentos.json')
        shutil.copytree(sample / 'documentos', folder / 'documentos')
        meta = build_index(folder)
        connection = check_connection(folder)
        audit = ParecerAuditoria(linhas_analisadas=list(range(1, len(records) + 1)),
            suspeitos=[Achado(linha=109, motivo_suspeita='valor objeto contrato')], relatorio_markdown='Teste isolado RAG')
        result = retrieve_for_agents(folder, records, audit)[109]
        assert result['fontes'] and all(s['linha'] == 109 for s in result['fontes'])
        proof = {'indice': meta, 'mcp': connection, 'linha': 109,
            'fontes': [{k: s[k] for k in ('id', 'pagina', 'documento_id', 'sha256_pdf', 'tipo_documento')} for s in result['fontes']],
            'chamadas_IA': 0, 'chamadas_rede': 0,
            'originais_preservados': before == {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in before}}
        assert proof['originais_preservados']
    out = ROOT / 'data/raw/rag_verificacao'
    out.mkdir(exist_ok=True)
    (out / 'verificacao.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(proof, ensure_ascii=False))


if __name__ == '__main__':
    main()
