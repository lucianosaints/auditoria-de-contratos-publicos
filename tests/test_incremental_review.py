import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.agent_review import ReviewSettings, review_saved_audit
from src.incremental_review import signature
from test_agent_review import audit_for, response


class IncrementalReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.records = [{'Objeto': f'Serviço demonstrativo do contrato {i}.'} for i in range(3)]
        self.audit = audit_for(3)
        (self.folder / 'parecer.json').write_text(self.audit.model_dump_json(), encoding='utf-8')
        self.calls = []

    def run_review(self, incremental=True):
        def worker(llm, stage, dossiers, skills, previous=None, feedback=''):
            self.calls.append((stage, [d['linha'] for d in dossiers]))
            return response(stage, dossiers, previous)
        return review_saved_audit(SimpleNamespace(model='test-model'), self.folder, self.records, self.audit,
            ReviewSettings(interval_seconds=0), worker=worker, incremental=incremental)

    def test_only_changed_contract_is_sent_and_unchanged_resume_has_no_calls(self):
        first = self.run_review()
        self.assertEqual(len(first['itens']), 3); self.assertEqual(len(self.calls), 2)
        self.calls.clear()
        resumed = self.run_review()
        self.assertEqual(resumed['contratos_reaproveitados'], 3)
        self.assertEqual(resumed['status'], 'concluida'); self.assertEqual(self.calls, [])
        self.records[1]['Objeto'] += ' Informação nova.'
        changed = self.run_review()
        self.assertEqual(changed['contratos_reaproveitados'], 2)
        self.assertEqual(changed['contratos_pendentes'], 1)
        self.assertEqual(self.calls, [('investigacao', [2]), ('revisao', [2])])
        self.assertEqual({i['linha'] for i in changed['itens']}, {1, 2, 3})

    def test_legacy_batches_migrate_only_after_full_signature_validation(self):
        self.run_review(incremental=False)
        before = {p: p.read_bytes() for p in (self.folder / 'agentes/0001').glob('*.json')}
        self.calls.clear()
        self.records[1]['Objeto'] += ' Alteração relevante.'
        result = self.run_review()
        self.assertEqual(result['contratos_reaproveitados'], 2)
        self.assertEqual(self.calls, [('investigacao', [2]), ('revisao', [2])])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertTrue(list((self.folder / 'agentes/historico').glob('*/revisao_agentes.json')))

    def test_legacy_checkpoint_with_unknown_signature_is_not_reused(self):
        self.run_review(incremental=False); self.calls.clear()
        path = self.folder / 'agentes/0001/investigacao.json'
        data = json.loads(path.read_text(encoding='utf-8')); data['assinatura'] = 'desconhecida'
        path.write_text(json.dumps(data), encoding='utf-8')
        result = self.run_review()
        self.assertEqual(result['contratos_reaproveitados'], 0)
        self.assertEqual(self.calls, [('investigacao', [1, 2, 3]), ('revisao', [1, 2, 3])])

    def test_bad_contract_cache_cannot_restore_invented_evidence(self):
        self.run_review(); self.calls.clear()
        path = self.folder / 'agentes/por_contrato/2.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['revisao']['evidencias'][0]['trecho'] = 'Citação inventada.'
        path.write_text(json.dumps(data), encoding='utf-8')
        result = self.run_review()
        self.assertEqual(result['contratos_reaproveitados'], 2)
        self.assertEqual(self.calls, [('investigacao', [2]), ('revisao', [2])])

    def test_global_index_changes_do_not_invalidate_other_contracts(self):
        dossier = {'linha': 1, 'documentos': {'rag_assinatura': 'global-v1', 'assinatura': 'local-v1'},
                   'fontes': [{'texto': 'Texto exato da página 9.'}]}
        original = signature(dossier, 'm', 's', 'p')
        changed = copy.deepcopy(dossier); changed['documentos']['rag_assinatura'] = 'global-v2'
        self.assertEqual(original, signature(changed, 'm', 's', 'p'))
        changed['documentos']['assinatura'] = 'local-v2'
        self.assertNotEqual(original, signature(changed, 'm', 's', 'p'))
        self.assertNotEqual(original, signature(dossier, 'new-model', 's', 'p'))
