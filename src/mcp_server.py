"""Servidor MCP stdio somente de leitura, restrito às execuções locais."""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from src.rag import ROOT, run_folder, search, status

server = FastMCP('Auditoria Cidadã — evidências locais')
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


@server.tool(annotations=READ_ONLY)
def estado_indice(execucao: str) -> dict:
    """Informa cobertura e atualização do índice RAG de uma execução local."""
    return status(run_folder(execucao))


@server.tool(annotations=READ_ONLY)
def buscar_evidencias(execucao: str, linha: int, consulta: str, limite: int = 5) -> dict:
    """Busca trechos literais somente do contrato/linha solicitado. Inclui página, URL, hash e limites de OCR; nenhum resultado não prova ausência."""
    return search(run_folder(execucao), linha, consulta, limite)


@server.tool(annotations=READ_ONLY)
def consultar_indicadores(execucao: str, linha: int | None = None, limite_fornecedores: int = 10) -> dict:
    """Consulta indicadores salvos e atuais: cobertura e distribuição de valores contratuais. Não são pagamentos ou prova de irregularidade. Não gera arquivos nem consulta rede."""
    from src.management_analytics import saved_indicators
    return saved_indicators(run_folder(execucao), linha, limite_fornecedores)


if __name__ == '__main__':
    server.run(transport='stdio')
