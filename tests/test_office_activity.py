import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.office_activity import activity, observe_activity, saved_activity, source_activity, source_request
from src.ui_jobs import run_job


class OfficeActivityTests(unittest.TestCase):
    def test_source_reports_request_completion_failure_and_cache_without_query_tokens(self):
        events = []
        with observe_activity(Path('.'), lambda *args: None, lambda *args: events.append(args)):
            with source_request('https://pncp.gov.br/api/consulta/v1/contratos?token=secret', 'PNCP'):
                pass
            with self.assertRaises(ValueError):
                with source_request('https://www.marica.rj.gov.br/diario', 'Diário'):
                    raise ValueError('fixture')
            source_activity('https://pncp.gov.br/api/consulta/v1/contratos', 'PNCP', 'cache_local')
            source_activity('javascript:alert(1)', 'Inválido')
            source_activity('https://user:secret@example.com/path', 'Inválido')
        self.assertEqual([e[2] for e in events], ['consultando', 'resposta_recebida', 'consultando', 'falhou', 'cache_local'])
        self.assertNotIn('secret', str(events))

    def test_job_tracks_actual_source_switches_and_keeps_cache_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); jobs = root / 'jobs'; jobs.mkdir()
            path = jobs / 'sourcejob.json'
            path.write_text(json.dumps({'id': 'sourcejob', 'action': 'consultar_pncp', 'run_id': 'run1'}), encoding='utf-8')
            def operation(action, run):
                with source_request('https://transparencia.marica.rj.gov.br/contratos', 'Portal'):
                    pass
                with source_request('https://transparencia.marica.rj.gov.br/contratos/1', 'Portal'):
                    pass
                with source_request('https://pncp.gov.br/api/contratos', 'PNCP'):
                    pass
                source_activity('https://pncp.gov.br/api/contratos/1', 'PNCP', 'cache_local')
                return 0, {}
            with patch('src.ui_jobs.ROOT', root):
                self.assertEqual(run_job('sourcejob', jobs_root=jobs, operation=operation, monitor_cancel=False), 0)
            office = json.loads(path.read_text(encoding='utf-8'))['office']
            self.assertEqual([s['name'] for s in office['sources']], ['Portal', 'PNCP'])
            self.assertEqual([s['requests'] for s in office['sources']], [2, 1])
            self.assertEqual(office['source']['status'], 'cache_local')

    def test_events_only_for_selected_folder_and_successfully_published_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'selected'
            events = []
            with observe_activity(folder, lambda a, p: events.append((a, p))):
                saved_activity(folder / 'progresso.json', {'status': 'analisando', 'fase_atual': 'aguardando_cota'})
                saved_activity(folder / 'revisao_agentes.json', {'status': 'em_andamento', 'etapa_atual': 'revisao'})
                saved_activity(folder / 'revisao_agentes.json', {'status': 'interrompida', 'etapa_atual': 'revisao'})
                activity(folder.parent / 'other', 0)
            activity(folder, 2)
            self.assertEqual(events, [(1, 'aguardando_cota'), (4, 'trabalhando'), (None, 'trabalhando')])

    def test_job_preserves_fast_transitions_and_deduplicates_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); jobs = root / 'jobs'; jobs.mkdir()
            path = jobs / 'job1.json'
            path.write_text(json.dumps({'id': 'job1', 'action': 'nova_auditoria', 'run_id': 'run1'}), encoding='utf-8')
            def operation(action, run):
                folder = root / 'data/reports' / run
                for agent in [0, 1, 1, 3, 4, 2]:
                    activity(folder, agent)
                return 0, {}
            with patch('src.ui_jobs.ROOT', root):
                self.assertEqual(run_job('job1', jobs_root=jobs, operation=operation, monitor_cancel=False), 0)
            result = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual([e['agent'] for e in result['office']['events']], [0, 1, 3, 4, 2])
            self.assertEqual([e['seq'] for e in result['office']['events']], [1, 2, 3, 4, 5])
            self.assertEqual(result['status'], 'concluido')

    def test_telemetry_io_failure_does_not_stop_the_work(self):
        def failed(*args):
            raise PermissionError('fixture')
        with observe_activity(Path('.'), failed):
            activity(Path('.'), 0)
