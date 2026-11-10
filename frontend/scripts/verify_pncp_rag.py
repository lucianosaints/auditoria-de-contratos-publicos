"""Verificação local dos PDFs PNCP no MCP, sem IA ou rede externa."""
import asyncio
import json
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))


if __name__ == '__main__':
    from src.atomic_files import write_json
    from src.rag import build_index
    from src.rag_client import request
    folder = ROOT / 'data/reports/20261020T015002Z_72b23869'
    summary = build_index(folder)
    results, connection = asyncio.run(request(folder, {31: 'cláusula valor pagamento'}))
    sources = results[31]['fontes']
    assert any(s.get('origem') == 'pncp' for s in sources), sources
    proof = {'indice': summary, 'mcp': connection,
             'fontes': [{k: s.get(k) for k in ('id', 'origem', 'numero_controle_pncp', 'pagina', 'sha256_pdf')} for s in sources],
             'chamadas_ia': 0, 'rede_externa': 0}
    write_json(ROOT / 'data/raw/pncp_verificacao_20261021/verificacao_mcp.json', proof)
    print(json.dumps(proof, ensure_ascii=True, indent=2))
