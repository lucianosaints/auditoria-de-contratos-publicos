import json
import unittest
import tempfile
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.audit_models import Achado, ParecerAuditoria
from src.database import ContratoAuditado, init_db, salvar_contratos
from src.tools.archive_tool import parse_brl, prepare_records
from src.tools.extrator_api_tool import ExtratorContratosMarica
from src.tasks.collect_contracts import validate_collection
from crewai.tasks.task_output import TaskOutput


def html(number: int, following: str = "") -> str:
    return f'<table><thead><tr><th>Objeto</th></tr></thead><tbody><tr><td>{number}</td></tr></tbody></table>{following}'


class Phase3Tests(unittest.TestCase):
    def setUp(self) -> None:
        enrichment = patch('src.tools.extrator_api_tool.enrich_contracts')
        self.enrichment = enrichment.start()
        self.addCleanup(enrichment.stop)

    def browser_page(self, playwright: Mock) -> Mock:
        browser = playwright.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_page.return_value
        page.locator.return_value.count.return_value = 0
        page.locator.return_value.filter.return_value.count.return_value = 0
        return page

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_all_rows_and_long_content(self, playwright: Mock) -> None:
        rows = ''.join(f'<tr><td>{i}{"x" * 1600}</td></tr>' for i in range(8))
        page = self.browser_page(playwright)
        page.content.return_value = f'<table><thead><tr><th>Objeto</th></tr></thead><tbody>{rows}</tbody></table>'
        records = json.loads(ExtratorContratosMarica()._run())
        self.assertEqual(len(records), 8)
        self.assertGreater(len(records[-1]['Objeto']), 1500)
        page.select_option.assert_called_once_with("select[name='year']", '2026', timeout=5000)
        playwright.return_value.__enter__.return_value.chromium.launch.return_value.close.assert_called_once()

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_browser_failure_is_rejected_by_collection(self, playwright: Mock) -> None:
        page = self.browser_page(playwright)
        page.goto.side_effect = RuntimeError('navegacao indisponivel')
        raw = ExtratorContratosMarica()._run()
        self.assertIn('Erro', json.loads(raw)[0])
        output = TaskOutput(description='teste', raw=raw, agent='teste')
        self.assertFalse(validate_collection(output)[0])

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_unconfirmed_year_stops_collection(self, playwright: Mock) -> None:
        page = self.browser_page(playwright)
        page.select_option.side_effect = RuntimeError('Filtro indisponivel')
        result = json.loads(ExtratorContratosMarica()._run())
        self.assertIn('Erro', result[0])
        page.content.assert_not_called()
        self.enrichment.assert_not_called()

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_csv_export_saved_separately(self, playwright: Mock) -> None:
        page = self.browser_page(playwright)
        page.content.return_value = html(1)
        next_button = page.locator.return_value.filter.return_value
        # Sem Próximo; um link CSV na etapa de exportação.
        next_button.count.side_effect = [0, 1]
        with tempfile.TemporaryDirectory() as directory:
            tool = ExtratorContratosMarica(output_dir=Path(directory))
            self.assertEqual(json.loads(tool._run()), [{'Objeto': '1'}])
            page.expect_download.return_value.__enter__.return_value.value.save_as.assert_called_once_with(
                str(Path(directory) / 'exportacao_portal.csv'))
            receipt = json.loads((Path(directory) / 'exportacao.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['status'], 'salvo')
            self.assertEqual(receipt['completude'], 'não verificada')

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_disabled_next_is_not_clicked(self, playwright: Mock) -> None:
        page = self.browser_page(playwright)
        page.content.return_value = html(1)
        next_button = page.locator.return_value.filter.return_value
        next_button.count.return_value = 1
        next_button.first.locator.return_value.get_attribute.return_value = 'disabled'
        self.assertEqual(json.loads(ExtratorContratosMarica()._run()), [{'Objeto': '1'}])
        next_button.first.click.assert_not_called()

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_multiple_pages(self, playwright: Mock) -> None:
        page = self.browser_page(playwright)
        page.content.side_effect = [html(1), html(2)]
        next_button = page.locator.return_value.filter.return_value
        next_button.count.side_effect = [1, 1, 0, 0]
        next_button.first.locator.return_value.get_attribute.return_value = ''
        result = json.loads(ExtratorContratosMarica()._run())
        self.assertEqual(result, [{'Objeto': '1'}, {'Objeto': '2'}])
        next_button.first.click.assert_called_once_with(timeout=5000)

    @patch('src.tools.extrator_api_tool.sync_playwright')
    def test_explicit_other_year_is_filtered(self, playwright: Mock) -> None:
        page = self.browser_page(playwright)
        page.content.return_value = ('<table><thead><tr><th>Objeto</th><th>Período de Vigência</th>'
            '</tr></thead><tbody><tr><td>antigo</td><td>2025</td></tr>'
            '<tr><td>atual</td><td>2026</td></tr></tbody></table>')
        self.assertEqual(json.loads(ExtratorContratosMarica()._run()),
                         [{'Objeto': 'atual', 'Período de Vigência': '2026'}])

    def test_brl_and_coverage(self) -> None:
        self.assertEqual(parse_brl('R$ 1.234,56'), Decimal('1234.56'))
        self.assertEqual(parse_brl('0,00'), Decimal('0.00'))
        self.assertIsNone(parse_brl(None))
        self.assertEqual(parse_brl('1234.56'), Decimal('1234.56'))
        self.assertEqual(parse_brl('R$ 1.234.567,89'), Decimal('1234567.89'))
        for invalid in ('1.234', '12.34,56', '1,234.56', 'NaN', 'Infinity', '1e3'):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                parse_brl(invalid)
        audit = ParecerAuditoria(linhas_analisadas=[], suspeitos=[], relatorio_markdown='teste')
        self.assertEqual(prepare_records([{'Objeto': 'teste'}], audit), [])

    def test_persistence_idempotency_and_rollback_sqlite(self) -> None:
        # Teste local transacional; não substitui integração PostgreSQL real.
        engine = create_engine('sqlite://')
        init_db(engine)
        audit = ParecerAuditoria(linhas_analisadas=[1], suspeitos=[Achado(linha=1, motivo_suspeita='Valor zero, conferir')], relatorio_markdown='teste')
        records = prepare_records([{'Número do Processo': '1', 'Nome do Beneficiário': 'A', 'Objeto': 'B', 'Valor do Contrato': '0,00'}], audit)
        self.assertEqual(salvar_contratos(records, engine)['inseridos'], 1)
        self.assertEqual(salvar_contratos(records, engine)['ja_existentes'], 1)
        good = records[0].model_copy(update={'fingerprint': 'a' * 64})
        bad = records[0].model_copy(update={'fingerprint': 'b' * 64, 'situacao_auditoria': 'Invalido'})
        with self.assertRaises(Exception):
            salvar_contratos([good, bad], engine)
        with Session(engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(ContratoAuditado)), 1)
        engine.dispose()
