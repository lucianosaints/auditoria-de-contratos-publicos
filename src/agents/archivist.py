from crewai import Agent, LLM
from src.tools.archive_tool import ArquivarContratosTool


def create_archivist(llm: LLM, tool: ArquivarContratosTool) -> Agent:
    return Agent(
        role="Agente Arquivista de Dados",
        goal="Persistir apenas suspeitos do parecer validado com fidelidade à fonte.",
        backstory="Especialista em arquivamento. Não reclassifica pareceres nem inventa contratos.",
        llm=llm, tools=[tool], allow_delegation=False, max_iter=3,
        respect_context_window=False, verbose=True,
    )
