from pathlib import Path
from crewai import Crew, LLM, Process

from src.agents.auditor import create_auditor
from src.agents.collector import create_collector
from src.tasks.audit_contracts import create_audit_task
from src.tasks.collect_contracts import create_collection_task
from src.tools.extrator_api_tool import ExtratorContratosMarica
from src.agents.archivist import create_archivist
from src.tasks.archive_contracts import create_archive_task
from src.tools.archive_tool import ArquivarContratosTool


def create_crew(llm: LLM, output_dir: Path) -> Crew:
    output_dir.mkdir(parents=True, exist_ok=False)
    tool = ExtratorContratosMarica(output_dir=output_dir)
    tool.result_as_answer = True
    collector = create_collector(llm, tool)
    auditor = create_auditor(llm)
    collection = create_collection_task(collector, output_dir / "contratos.json")
    audit = create_audit_task(auditor, collection, output_dir / "parecer.json")
    archive_tool = ArquivarContratosTool(output_dir=output_dir, result_as_answer=True)
    archivist = create_archivist(llm, archive_tool)
    archive = create_archive_task(archivist, audit, archive_tool, output_dir / "arquivamento.json")
    return Crew(
        agents=[collector, auditor, archivist], tasks=[collection, audit, archive],
        process=Process.sequential, memory=False, cache=False, verbose=True,
    )
