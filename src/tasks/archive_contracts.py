from pathlib import Path
from crewai import Agent, Task
from src.tools.archive_tool import ArquivarContratosTool


def create_archive_task(agent: Agent, audit: Task, tool: ArquivarContratosTool, destination: Path) -> Task:
    return Task(
        description=(
            "Receba o parecer e execute obrigatoriamente arquivar_contratos_suspeitos "
            "sem argumentos. A ferramenta extrai os índices estruturados dos suspeitos "
            "e recupera os campos originais da coleta para salvar no PostgreSQL. "
            "Não reformule dados nem declare sucesso sem confirmação da ferramenta."
        ),
        expected_output="Recibo JSON confirmado com recebidos, inseridos e ja_existentes.",
        agent=agent, context=[audit], guardrail=tool.validate_receipt,
        guardrail_max_retries=0, output_file=str(destination),
    )
