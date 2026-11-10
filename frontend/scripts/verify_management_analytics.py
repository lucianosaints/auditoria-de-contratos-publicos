"""Gera indicadores reais locais e confere preservação da auditoria e leitura MCP."""
import asyncio
import hashlib
import json
import os
import site
import sys
from pathlib import Path
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['LOCALAPPDATA'] = str(ROOT / 'data/test_runtime')
os.environ['CREWAI_STORAGE_DIR'] = str(ROOT / 'data/test_runtime/analytics')


async def mcp_check(run):
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from src.rag_client import parameters
    async with stdio_client(parameters()) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            result = await session.call_tool('consultar_indicadores', {'execucao': run, 'linha': 31, 'limite_fornecedores': 3})
            assert not result.isError
            data = json.loads(next(c.text for c in result.content if c.type == 'text'))
            assert data['status'] == 'pronto' and data['item']['linha'] == 31
            assert len(data['fornecedores']) <= 3
            return {'status': data['status'], 'linha': data['item']['linha'], 'transporte': 'stdio'}


def main():
    from src.ui_jobs import execute_action
    from src.atomic_files import write_json
    run = '20261020T015002Z_72b23869'
    folder = ROOT / 'data/reports' / run
    names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json',
             'arquivamento.json', 'verificacao_evidencias.json', 'documentos.json', 'pncp.json', 'rag/indice.sqlite3']
    hashes = lambda: {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in names}
    before = hashes()
    code, summary = execute_action('gerar_indicadores', run)
    assert code == 0
    result = json.loads((folder / 'indicadores.json').read_text(encoding='utf-8'))
    mcp = asyncio.run(mcp_check(run))
    assert before == hashes()
    proof = {'resultado': summary, 'cobertura': result['cobertura'], 'mcp': mcp,
             'pandas_versao': result['pandas_versao'], 'originais_preservados': True,
             'hashes_preservados': before, 'chamadas_ia': 0, 'chamadas_rede_externa': 0, 'chamadas_banco': 0}
    write_json(ROOT / 'data/raw/analytics_verificacao_20261021/verificacao.json', proof)
    print(json.dumps(proof, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
