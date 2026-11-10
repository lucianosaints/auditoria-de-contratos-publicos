"""Cliente MCP real; prepara contexto dos agentes sem novas chamadas de IA."""
import asyncio
import json
import sys
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.rag import ROOT, database, status


def parameters():
    # Usa o mesmo interpretador e site-packages do executor, inclusive fora da venv.
    bootstrap = 'import sys; sys.path[:0]=' + repr(sys.path) + '; from src.mcp_server import server; server.run(transport="stdio")'
    return StdioServerParameters(command=sys.executable, args=['-c', bootstrap], cwd=str(ROOT))


async def request(folder, queries):
    async with stdio_client(parameters()) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            tools = await session.list_tools()
            results = {}
            for line, query in queries.items():
                result = await session.call_tool('buscar_evidencias', {'execucao': folder.name, 'linha': line, 'consulta': query[:2000], 'limite': 5})
                if result.isError:
                    raise ValueError('Falha na busca MCP: ' + ' '.join(c.text for c in result.content if c.type == 'text'))
                results[line] = json.loads(next(c.text for c in result.content if c.type == 'text'))
            state = await session.call_tool('estado_indice', {'execucao': folder.name})
            if state.isError:
                raise ValueError('O MCP não conseguiu verificar o índice desta execução.')
            return results, {'transporte': 'stdio', 'conectado': True,
                'ferramentas': [t.name for t in tools.tools],
                'indice': json.loads(next(c.text for c in state.content if c.type == 'text'))}


def check_connection(folder):
    return asyncio.run(request(folder, {}))[1]


def retrieve_for_agents(folder, records, audit):
    if not database(folder).exists():
        return None  # Compatibilidade: sem índice, mantém leitura inicial anterior.
    state = status(folder)
    if state['status'] != 'pronto':
        raise ValueError('RAG indisponível ou desatualizado. Use Preparar RAG antes de revisar.')
    reasons = {}
    for finding in audit.suspeitos:
        reasons.setdefault(finding.linha, []).append(finding.motivo_suspeita)
    queries = {line: ' '.join(values)[:1500] + ' ' + ' '.join(v[:300] for k, v in records[line - 1].items() if 'objeto' in k.casefold())[:499] for line, values in reasons.items()}
    return asyncio.run(request(folder, queries))[0]
