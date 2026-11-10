"""Telemetria visual da ação local, sem alterar decisões ou checkpoints."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import logging
from urllib.parse import urlsplit, urlunsplit

_listener = ContextVar('office_listener', default=None)


@contextmanager
def observe_activity(folder, callback, source_callback=None):
    token = _listener.set((Path(folder).resolve(), callback, source_callback))
    try:
        yield
    finally:
        _listener.reset(token)


def activity(folder, agent, phase='trabalhando'):
    listener = _listener.get()
    if listener and Path(folder).resolve() == listener[0]:
        try:
            listener[1](agent, phase)
        except OSError:
            logging.warning('Telemetria visual indisponível; operação principal preservada.')


def source_activity(url, name, status='consultando'):
    listener = _listener.get()
    if not listener or not listener[2]:
        return
    parsed = urlsplit(url)
    if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or parsed.password:
        return
    # Não publica parâmetros de sessão, chaves ou tokens presentes na query.
    public_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
    try:
        listener[2](name, public_url, status)
    except OSError:
        logging.warning('Telemetria de fontes indisponível; consulta principal preservada.')


@contextmanager
def source_request(url, name):
    source_activity(url, name)
    try:
        yield
    except BaseException:
        source_activity(url, name, 'falhou')
        raise
    else:
        source_activity(url, name, 'resposta_recebida')


class DocumentSourceSession:
    """Observa somente downloads reais, mantendo a política documental intacta."""
    def __init__(self, session):
        self.session = session

    @contextmanager
    def get(self, url, **kwargs):
        with source_request(url, 'Documentos oficiais · download de PDF'), self.session.get(url, **kwargs) as response:
            yield response


def saved_activity(path, value):
    path = Path(path)
    if not isinstance(value, dict):
        return
    if path.name == 'progresso.json':
        agent = {'analisando': 1, 'consultando_diario': 0, 'arquivando': 2}.get(value.get('status'))
    elif path.name == 'revisao_agentes.json':
        agent = {'investigacao': 3, 'revisao': 4}.get(value.get('etapa_atual'))
        if value.get('status') in {'interrompida', 'concluida', 'sem_achados'}:
            agent = None
    else:
        return
    activity(path.parent, agent, value.get('fase_atual', 'trabalhando'))
