import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.audit_models import Achado, ParecerAuditoria
from src.tools.archive_tool import ArquivarContratosTool, prepare_records


class ArchiveIndicesTests(unittest.TestCase):
    def records(self):
        return [{"Processo": "A", "Objeto": "primeiro"}, {"Processo": "B", "Objeto": "segundo"}]

    def audit(self, lines, findings):
        return ParecerAuditoria(
            linhas_analisadas=lines,
            suspeitos=[Achado(linha=line, motivo_suspeita=reason) for line, reason in findings],
            relatorio_markdown="teste",
        )

    def test_incomplete_coverage_does_not_block_valid_suspect(self):
        warnings = []
        result = prepare_records(self.records(), self.audit([], [(2, "conferir")]), warnings)
        self.assertEqual([r.numero_processo for r in result], ["B"])
        self.assertEqual(warnings[0]["tipo"], "cobertura_incompleta_ou_inconsistente")

    def test_bad_indices_are_skipped_without_guessing(self):
        warnings = []
        result = prepare_records(self.records(), self.audit([1, 2], [(0, "zero"), (-1, "negativo"), (99, "fora"), (1, "valido")]), warnings)
        self.assertEqual([r.numero_processo for r in result], ["A"])
        self.assertEqual([w["linha"] for w in warnings], [0, -1, 99])

    def test_duplicates_merge_unique_reasons(self):
        result = prepare_records(self.records(), self.audit([1, 2], [(1, "A"), (1, "B"), (1, "A")]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].motivo_suspeita, "A\nB")

    def test_empty_records_and_no_suspects(self):
        self.assertEqual(prepare_records([], self.audit([], [(1, "fora")])), [])
        self.assertEqual(prepare_records(self.records(), self.audit([], [])), [])

    @patch("src.tools.archive_tool.salvar_contratos")
    def test_tool_saves_only_matched_records_and_reports_skips(self, save):
        save.return_value = {"recebidos": 1, "inseridos": 1, "ja_existentes": 0}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "contratos.json").write_text(json.dumps(self.records()), encoding="utf-8")
            (folder / "parecer.json").write_text(self.audit([], [(2, "valido"), (99, "fora")]).model_dump_json(), encoding="utf-8")
            tool = ArquivarContratosTool(output_dir=folder)
            receipt = json.loads(tool._run())
            self.assertEqual(save.call_args.args[0][0].numero_processo, "B")
            self.assertEqual(receipt["inseridos"], 1)
            self.assertEqual(receipt["ignorados"], 1)
            self.assertEqual(receipt["status"], "concluido_com_avisos")
            self.assertEqual(json.loads(tool._run()), receipt)
            save.assert_called_once()

    @patch("src.tools.archive_tool.salvar_contratos")
    def test_no_matching_indices_does_not_connect_to_database(self, save):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "contratos.json").write_text("[]", encoding="utf-8")
            (folder / "parecer.json").write_text(self.audit([], [(1, "fora")]).model_dump_json(), encoding="utf-8")
            receipt = json.loads(ArquivarContratosTool(output_dir=folder)._run())
            self.assertEqual(receipt["inseridos"], 0)
            self.assertEqual(receipt["ignorados"], 1)
            save.assert_not_called()
