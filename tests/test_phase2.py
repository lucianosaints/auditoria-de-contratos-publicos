import json
import tempfile
import unittest
from pathlib import Path

from crewai import LLM
from crewai.tasks.task_output import TaskOutput

from src.crew import create_crew
from src.tasks.collect_contracts import validate_collection


class Phase2Tests(unittest.TestCase):
    def output(self, raw: str) -> TaskOutput:
        return TaskOutput(description="teste", raw=raw, agent="teste")

    def test_collection_preserves_records_and_rejects_errors(self) -> None:
        records = [{"Número do Processo": "123", "Valor": "R$ 0,00"}]
        ok, clean = validate_collection(self.output(json.dumps(records)))
        self.assertTrue(ok)
        self.assertEqual(json.loads(clean), records)
        for invalid in ["Erro na API", "{}", "[{}]", '[{"Valor": null}]']:
            self.assertFalse(validate_collection(self.output(invalid))[0])
        self.assertTrue(validate_collection(self.output("[]"))[0])

    def test_crew_wiring_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            llm = LLM(model="openai/gpt-4o-mini", api_key="test-only", temperature=0)
            crew = create_crew(llm, Path(directory) / "run")
            self.assertEqual(len(crew.agents), 3)
            self.assertEqual(len(crew.tasks), 3)
            self.assertEqual(len(crew.agents[0].tools), 1)
            self.assertEqual(crew.agents[1].tools, [])
            self.assertTrue(crew.agents[0].tools[0].result_as_answer)
            self.assertIs(crew.tasks[1].context[0], crew.tasks[0])
            self.assertTrue(all(not agent.allow_delegation for agent in crew.agents))


if __name__ == "__main__":
    unittest.main()
