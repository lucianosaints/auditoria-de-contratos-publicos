import copy
import unittest

from src.quality_evaluation import make_sample, evaluate, render_report
from src.quality_pilot import initialize, analyze, FIELDS


class QualityPilotTests(unittest.TestCase):
    def setUp(self):
        self.records = [{'Objeto': 'Caso fictício 1'}, {'Objeto': 'Caso fictício 2'}]
        self.audit = {'suspeitos': [{'linha': 1}]}
        self.ref = initialize(make_sample(self.records, self.audit, 1), {'documentos.json': 'snapshot'})

    def close(self, index=0, decision=True):
        base, item = self.ref['itens'][index], self.ref['piloto']['itens'][index]
        base.update(exige_diligencia=decision, responsavel='Pessoa fictícia', justificativa='Conferido', fontes=['Fonte p. 1'])
        item.update(encerrado_em='2026-10-23T18:00:00+00:00', manual_segundos=120,
                    avaliacao_independente={f: copy.deepcopy(base[f]) for f in FIELDS},
                    rascunho={f: copy.deepcopy(base[f]) for f in FIELDS})

    def test_empty_pilot_does_not_invent_metrics_or_time_savings(self):
        result = evaluate(self.records, self.audit, self.ref)
        self.assertEqual(result['pendentes'], 2)
        self.assertIsNone(result['precisao'])
        self.assertIsNone(result['piloto']['conferencia_independente']['total_segundos'])
        self.assertIsNone(result['piloto']['tempo_economizado_segundos'])
        self.assertIn('Tempo economizado: não estimável', render_report(result))

    def test_assisted_change_cannot_change_reference_metrics(self):
        self.close()
        p = self.ref['piloto']['itens'][0]
        p.update(triagem_aberta_em='2026-10-23T18:01:00+00:00', sistema_segundos=30,
                 reavaliacao_assistida={'exige_diligencia': False, 'justificativa': 'Mudei após consultar'})
        result = evaluate(self.records, self.audit, self.ref)
        self.assertEqual(result['verdadeiros_positivos'], 1)
        self.assertEqual(result['piloto']['consulta_posterior_ao_sistema']['total_segundos'], 30)
        self.assertEqual(result['piloto']['reavaliacoes_comparaveis'], 1)
        self.assertEqual(result['piloto']['mudancas_de_decisao_apos_consulta'], 1)
        self.ref['itens'][0]['exige_diligencia'] = False
        with self.assertRaisesRegex(ValueError, 'alterada'):
            evaluate(self.records, self.audit, self.ref)

    def test_prior_exposure_is_excluded_from_accuracy(self):
        self.close()
        self.ref['piloto']['itens'][0]['exposicao_previa'] = True
        result = evaluate(self.records, self.audit, self.ref)
        self.assertEqual(result['avaliados'], 0)
        self.assertEqual(result['pendentes'], 2)
        self.assertIsNone(result['precisao'])

    def test_invalid_timing_order_identity_and_duplicate_cases_rejected(self):
        self.close()
        for mutation in ('negative', 'boolean', 'nan', 'early', 'duplicate', 'id', 'not_closed'):
            with self.subTest(mutation=mutation):
                ref = copy.deepcopy(self.ref)
                p = ref['piloto']['itens'][0]
                if mutation == 'negative': p['manual_segundos'] = -1
                elif mutation == 'boolean': p['manual_segundos'] = True
                elif mutation == 'nan': p['manual_segundos'] = float('nan')
                elif mutation == 'early': p['triagem_aberta_em'] = '2026-10-23T17:00:00+00:00'
                elif mutation == 'duplicate': ref['piloto']['itens'][1] = copy.deepcopy(p)
                elif mutation == 'id': ref['piloto']['id'] = 'outro'
                else: p['encerrado_em'] = None
                with self.assertRaises(ValueError): analyze(ref)

    def test_draft_decisions_are_not_published_as_reference(self):
        self.ref['piloto']['itens'][0]['rascunho']['exige_diligencia'] = True
        result = evaluate(self.records, self.audit, self.ref)
        self.assertEqual(result['avaliados'], 0)
        self.assertEqual(result['pendentes'], 2)
