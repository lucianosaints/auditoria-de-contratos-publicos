"""Procedimentos locais do aplicativo; não são skills instaladas no Codex."""
import hashlib
import json
import re
from pathlib import Path

from src.tools.archive_tool import normalized

SKILLS_ROOT = Path(__file__).with_name('audit_skills')
SKILL_NAMES = ('documental', 'cobertura_contratual', 'precos_e_escopo', 'atas', 'revisao')


def load_skills():
    return {name: (SKILLS_ROOT / f'{name}.md').read_text(encoding='utf-8') for name in SKILL_NAMES}


def select_skills(record, reasons):
    # Ativação é uma seleção de procedimentos, nunca um novo achado.
    text = normalized(' '.join([*record.values(), *reasons]))
    selected = ['documental', 'revisao']
    if any(term in text for term in ('sem cobertura', 'sem contrato', 'indeniz', 'reconhecimento de divida')):
        selected.append('cobertura_contratual')
    if any(term in text for term in ('preco', 'custo', 'quantit', 'modular', 'escopo', 'zerado', 'valor zero')):
        selected.append('precos_e_escopo')
    if re.search(r'\batas?\b', text) or any(term in text for term in ('registro de preco', 'adesao', 'anulada', 'anulacao')):
        selected.append('atas')
    return selected


def skills_digest(skills):
    data = json.dumps(skills, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()
