import json
import tempfile
import unittest
from pathlib import Path

from src.quality_evaluation import make_sample, evaluate
from src.quality_packet import build_packet


class QualityPacketTests(unittest.TestCase):
    def prepare(self, root):
        folder = root / 'run'; folder.mkdir()
        records = [{'Detalhe - Número': '1 - 2026', 'Objeto': '</script><img src=x onerror=alert(1)>',
                    'URL do contrato': 'javascript:alert(1)'}, {'Objeto': 'Segundo objeto'}]
        audit = {'suspeitos': [{'linha': 1, 'motivo_suspeita': 'Motivo de teste'}], 'linhas_analisadas': [1, 2]}
        reference = make_sample(records, audit, 1)
        for filename, data in [('contratos.json', records), ('parecer.json', audit)]:
            (folder / filename).write_text(json.dumps(data), encoding='utf-8')
        ref = root / 'reference.json'; ref.write_text(json.dumps(reference), encoding='utf-8')
        return folder, ref, records, audit

    def test_packet_keeps_pending_and_originals_and_escapes_script_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); folder, ref, records, audit = self.prepare(root)
            before = {p: p.read_bytes() for p in [ref, folder / 'contratos.json', folder / 'parecer.json']}
            result = build_packet(folder, ref, root / 'packet')
            self.assertTrue(all(i['exige_diligencia'] is None for i in result['referencia']['itens']))
            self.assertIsNone(result['casos'][0]['url_contrato'])
            initial = json.loads((root / 'packet/avaliacao_inicial.json').read_text(encoding='utf-8'))
            self.assertEqual(initial['pendentes'], 2); self.assertIsNone(initial['precisao'])
            html = (root / 'packet/avaliar.html').read_text(encoding='utf-8')
            self.assertNotIn('</script><img', html)
            self.assertIn('\\u003c/script\\u003e', html)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_incompatible_reference_is_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); folder, ref, _, _ = self.prepare(root)
            value = json.loads(ref.read_text()); value['coleta_sha256'] = 'changed'
            ref.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                build_packet(folder, ref, root / 'packet')
            self.assertFalse((root / 'packet').exists())

    def test_output_is_versioned_and_cannot_overwrite_existing_packet(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); folder, ref, _, _ = self.prepare(root)
            build_packet(folder, ref, root / 'packet')
            with self.assertRaisesRegex(ValueError, 'já existe'):
                build_packet(folder, ref, root / 'packet')

    def test_completed_fixture_decision_is_preserved_not_reinvented(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); folder, ref, records, audit = self.prepare(root)
            value = json.loads(ref.read_text()); item = value['itens'][0]
            item.update(exige_diligencia=True, responsavel='Pessoa fictícia de teste', justificativa='Justificativa da fixture', fontes=['Fonte fictícia de teste, página 1'])
            ref.write_text(json.dumps(value))
            packet = build_packet(folder, ref, root / 'packet')
            self.assertEqual(packet['referencia'], value)
            self.assertEqual(evaluate(records, audit, packet['referencia'])['avaliados'], 1)

    def test_pilot_is_new_snapshot_with_blank_identity_and_no_decisions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); folder, ref, records, audit = self.prepare(root)
            packet = build_packet(folder, ref, root / 'pilot', pilot=True)
            saved = json.loads((root / 'pilot/referencia_base.json').read_text(encoding='utf-8'))
            self.assertEqual(packet['referencia'], saved)
            self.assertEqual(saved['piloto']['avaliador']['nome'], '')
            self.assertTrue(all(p['manual_segundos'] is None for p in saved['piloto']['itens']))
            self.assertEqual(evaluate(records, audit, saved)['avaliados'], 0)
            self.assertIsNone(evaluate(records, audit, saved)['piloto']['tempo_economizado_segundos'])
            html = (root / 'pilot/avaliar.html').read_text(encoding='utf-8')
            self.assertIn('Encerrar conferência independente', html)
            self.assertNotIn('</script><img', html)

    def test_pilot_does_not_relabel_completed_reference_as_independent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); folder, ref, _, _ = self.prepare(root)
            value = json.loads(ref.read_text())
            value['itens'][0].update(exige_diligencia=True, responsavel='Pessoa fictícia',
                justificativa='Conferido', fontes=['Fonte de teste'])
            ref.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'sem decisões'):
                build_packet(folder, ref, root / 'pilot', pilot=True)
            self.assertFalse((root / 'pilot').exists())
