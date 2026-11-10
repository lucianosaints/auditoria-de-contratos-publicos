"""Metadados de andamento; não participa das regras de análise ou evidência."""
from datetime import datetime, timezone, timedelta


def set_phase(state, phase, seconds=0):
    now = datetime.now(timezone.utc)
    state.update(fase_atual=phase, fase_desde=now.isoformat(), atualizado_em=now.isoformat())
    state.pop('espera_ate', None)
    if seconds > 0:
        state['espera_ate'] = (now + timedelta(seconds=seconds)).isoformat()
