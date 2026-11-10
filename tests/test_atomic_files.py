import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from src.atomic_files import write_json


def blocked():
    error = PermissionError('Bloqueio transitório de teste')
    error.winerror = 5
    return error


class AtomicFilesTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Teste de compartilhamento de arquivos do Windows')
    def test_real_open_reader_is_tolerated_until_windows_releases_destination(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'estado.json'; path.write_text('{"antigo":true}', encoding='utf-8')
            reader = path.open('r', encoding='utf-8')
            release = threading.Timer(0.25, reader.close)
            delays = []
            def wait(seconds): delays.append(seconds); time.sleep(seconds)
            release.start()
            try:
                write_json(path, {'novo': True}, wait=wait)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'novo': True})
                self.assertTrue(delays, 'O leitor real deveria bloquear rename no Windows.')
            finally:
                release.join(); reader.close()

    def test_transient_windows_lock_preserves_old_json_until_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'progresso.json'
            path.write_text('{"antigo":true}', encoding='utf-8')
            replace = Path.replace
            attempts = []
            def flaky(source, target):
                attempts.append(source)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'antigo': True})
                if len(attempts) <= 2:
                    raise blocked()
                return replace(source, target)
            wait = Mock()
            with patch.object(Path, 'replace', flaky):
                write_json(path, {'texto': 'Revisão concluída'}, wait=wait)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'texto': 'Revisão concluída'})
            self.assertEqual(wait.call_count, 2)
            self.assertEqual(list(Path(name).glob('*.tmp')), [])

    def test_permanent_failure_does_not_destroy_previous_state(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'progresso.json'; path.write_text('original', encoding='utf-8')
            wait = Mock()
            with patch.object(Path, 'replace', side_effect=blocked()) as replace:
                with self.assertRaises(PermissionError):
                    write_json(path, {'novo': True}, attempts=3, wait=wait)
            self.assertEqual(replace.call_count, 3); self.assertEqual(wait.call_count, 2)
            self.assertEqual(path.read_text(encoding='utf-8'), 'original')
            self.assertEqual(list(Path(name).glob('*.tmp')), [])

    def test_temporary_names_are_unique_and_other_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'estado.json'; seen = []
            replace = Path.replace
            def recording(source, target): seen.append(source); return replace(source, target)
            with patch.object(Path, 'replace', recording):
                write_json(path, {'n': 1}); write_json(path, {'n': 2})
            self.assertNotEqual(seen[0], seen[1])
            wait = Mock()
            with patch.object(Path, 'replace', side_effect=OSError('Disco indisponível')) as replace:
                with self.assertRaises(OSError): write_json(path, {'n': 3}, wait=wait)
            self.assertEqual(replace.call_count, 1); wait.assert_not_called()
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'n': 2})
