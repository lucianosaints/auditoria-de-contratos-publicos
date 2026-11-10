from crewai import Agent, LLM
from src.tools.extrator_api_tool import ExtratorContratosMarica


def create_collector(llm: LLM, tool: ExtratorContratosMarica) -> Agent:
    return Agent(
        role="Agente Coletor de Dados Estruturados",
        goal="Executar a extração e transmitir o JSON integral sem alterar os dados.",
        backstory="Engenheiro de dados especializado em integridade de dados públicos.",
        llm=llm, tools=[tool], allow_delegation=False, max_iter=3, verbose=True,
        respect_context_window=False,
    )
