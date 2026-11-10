"""Publicação atômica com tolerância a bloqueios transitórios no Windows."""
import json
import os
import time
import uuid
from pathlib import Path


def write_json(path, value, *, attempts=10, wait=time.sleep):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        for number in range(attempts):
            try:
                temporary.replace(path)
                return
            except PermissionError as exc:
                if number == attempts - 1 or not (os.name == 'nt' or getattr(exc, 'winerror', None) in (5, 32, 33)):
                    raise
                wait(min(0.05 * 2 ** number, 0.5))
    finally:
        # Não toca no destino se não foi possível substituir. Uma limpeza
        # bloqueada também não deve mascarar o erro original ou o sucesso.
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
