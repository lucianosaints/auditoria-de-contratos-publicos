"""Adaptador inicial do portal: seletores e mapeamento ainda configuráveis."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from crewai.tools import BaseTool
from playwright.sync_api import (
    Error as PlaywrightError, Response, TimeoutError as PlaywrightTimeout,
    sync_playwright,
)
from pydantic import BaseModel, Field, ValidationError

from src.config import PORTAL_URL, ROOT, Settings

logger = logging.getLogger(__name__)


class SearchInput(BaseModel):
    exercise: int = Field(ge=2000, le=2100, description="Exercício da consulta")
    query: str = Field(default="", max_length=200, description="Trecho do objeto")
    limit: int = Field(default=10, ge=1, le=50)


def collect(settings: Settings, params: SearchInput) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    folder = ROOT / "data" / "raw" / run_id
    result: dict[str, Any] = {
        "ok": False, "source_url": PORTAL_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "filters": params.model_dump(), "records": [], "network": [],
        "ordering": "ordem apresentada pelo portal; recência não verificada",
        "artifacts_dir": str(folder), "error": None,
    }
    try:
        folder.mkdir(parents=True, exist_ok=False)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            try:
                context = browser.new_context(locale="pt-BR", accept_downloads=False)
                page = context.new_page()
                page.set_default_timeout(settings.timeout_ms)

                def capture(response: Response) -> None:
                    if response.request.resource_type not in {"xhr", "fetch"}:
                        return
                    if urlparse(response.url).hostname != urlparse(PORTAL_URL).hostname:
                        return
                    if len(result["network"]) >= 30:
                        return
                    entry: dict[str, Any] = {
                        "url": response.url, "method": response.request.method,
                        "status": response.status,
                        "content_type": response.headers.get("content-type", ""),
                        "request_body": (response.request.post_data or "")[:10000],
                    }
                    if "json" in entry["content_type"]:
                        try:
                            # Amostra limitada; os registros retornados vêm da tabela.
                            entry["response_sample"] = response.text()[:50000]
                        except PlaywrightError:
                            entry["response_sample_error"] = "Corpo indisponível"
                    result["network"].append(entry)

                page.on("response", capture)
                try:
                    response = page.goto(PORTAL_URL, wait_until="domcontentloaded")
                    if response is None or response.status >= 400:
                        raise RuntimeError(f"Falha HTTP inicial: {response.status if response else 'sem resposta'}")
                    exercise = page.locator(settings.exercise_selector)
                    # Falha em seletores ambíguos para evitar consultar outro campo.
                    exercise.wait_for(state="visible")
                    try:
                        exercise.select_option(label=str(params.exercise))
                    except PlaywrightError:
                        exercise.select_option(value=str(params.exercise))
                    if params.query:
                        page.locator(settings.object_selector).fill(params.query)
                    search = (
                        page.locator(settings.search_selector)
                        if settings.search_selector else page.get_by_text("Pesquisar", exact=True)
                    )
                    search.click()
                    rows_selector = f"{settings.table_selector} tbody tr"
                    ready_selectors = [rows_selector]
                    if settings.empty_selector:
                        ready_selectors.append(settings.empty_selector)
                    page.locator(", ".join(ready_selectors)).first.wait_for(state="visible")
                    empty = bool(settings.empty_selector) and page.locator(settings.empty_selector).is_visible()
                    if not empty:
                        table = page.locator(settings.table_selector)
                        if table.count() != 1:
                            raise RuntimeError("TABLE_SELECTOR deve identificar exatamente uma tabela")
                        result["columns"] = table.locator("thead th").all_inner_texts()
                        rows = table.locator("tbody tr")
                        for index in range(min(rows.count(), params.limit)):
                            row = rows.nth(index)
                            cells = row.locator("td").all_inner_texts()
                            if not cells or (len(cells) == 1 and row.locator("td[colspan]").count()):
                                raise RuntimeError("Linha de estado encontrada; configure EMPTY_SELECTOR ou aguarde a tabela")
                            links = row.locator("a[href]").evaluate_all(
                                "els => els.map(a => ({text: a.innerText, url: a.href}))"
                            )
                            result["records"].append({"cells": cells, "links": links})
                    result["ok"] = True
                finally:
                    # Preserva evidência mesmo quando o seletor ou a consulta falha.
                    for filename, action in [
                        ("page.html", lambda: (folder / "page.html").write_text(page.content(), encoding="utf-8")),
                        ("page.png", lambda: page.screenshot(path=str(folder / "page.png"), full_page=True)),
                    ]:
                        try:
                            action()
                        except (PlaywrightError, OSError):
                            logger.warning("Não foi possível salvar %s", filename, exc_info=True)
            finally:
                browser.close()
    except PlaywrightTimeout as exc:
        result["error"] = {"type": "timeout", "message": str(exc)}
    except (PlaywrightError, RuntimeError, OSError, ValueError) as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    except Exception as exc:
        logger.exception("Falha inesperada na coleta")
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    if not result["ok"]:
        result["records"] = []
    try:
        (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        result["ok"] = False
        result["error"] = {"type": "persistence_error", "message": str(exc)}
    return result


class ContractsScraperTool(BaseTool):
    name: str = "consultar_contratos_marica"
    description: str = "Consulta contratos por exercício e objeto; retorna JSON com evidências e erros explícitos."
    args_schema: type[BaseModel] = SearchInput
    settings: Settings = Field(default_factory=Settings, exclude=True)

    def _run(self, exercise: int, query: str = "", limit: int = 10) -> str:
        try:
            params = SearchInput(exercise=exercise, query=query, limit=limit)
        except ValidationError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return json.dumps(collect(self.settings, params), ensure_ascii=False)
