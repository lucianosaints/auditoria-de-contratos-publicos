import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTAL_URL = "https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao"


def get_portal_config() -> dict[str, str]:
    config_file = ROOT / "data" / "portal_config.json"
    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("url"):
                return {
                    "url": str(data["url"]).strip(),
                    "name": str(data.get("name") or "Município"),
                }
        except Exception:
            pass
    url = os.getenv("PORTAL_URL", DEFAULT_PORTAL_URL).strip()
    return {"url": url, "name": "Maricá - RJ" if "marica" in url.lower() else "Município"}


def get_portal_url() -> str:
    return get_portal_config()["url"]


PORTAL_URL = get_portal_url()


class Settings(BaseModel):
    model: str = "openai/gpt-4o-mini"
    headless: bool = True
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)
    exercise_selector: str = 'select[name*="exercicio" i]'
    object_selector: str = 'input[name*="objeto" i]'
    search_selector: str = ""
    table_selector: str = "table"
    empty_selector: str = ""


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    return Settings.model_validate({
        "model": os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
        "headless": os.getenv("HEADLESS", "true"),
        "timeout_ms": os.getenv("TIMEOUT_MS", "30000"),
        **{name: os.getenv(name.upper(), default) for name, default in {
            "exercise_selector": 'select[name*="exercicio" i]',
            "object_selector": 'input[name*="objeto" i]',
            "search_selector": "", "table_selector": "table",
            "empty_selector": "",
        }.items()},
    })
