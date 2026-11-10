import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.agent_review import (ReviewSettings, build_dossiers, main, review_saved_audit,
                              specialist_worker, split_dossiers, validate_stage, validation_feedback, parse_stage_response,
                              citation_catalog, stage_prompt)
from src.agent_skills import load_skills, select_skills
from src.audit_models import Achado, ParecerAuditoria


def audit_for(size=1):
    return ParecerAuditoria(linhas_analisadas=list(range(1, size + 1)),
        suspeitos=[Achado(linha=i, motivo_suspeita='Conferir cobertura contratual') for i in range(1, size + 1)],
        relatorio_markdown='Parecer original')


def response(stage, dossiers, previous=None):
    items = []
    for dossier in dossiers:
        source = next(s for s in dossier['fontes'] if len(s['texto']) >= 8)
        evidence = [{'fonte_id': source['id'], 'trecho': source['texto'][:60]}]
        common = {'linha': dossier['linha'], 'limite': 'Não comprova pagamento nem responsabilidade.', 'evidencias': evidence}
        if stage == 'investigacao':
            items.append({**common, 'observacao': 'A fonte apresenta o objeto publicado.'})
        else:
            common['evidencias'] = next(i['evidencias'] for i in previous['itens'] if i['linha'] == dossier['linha'])
            items.append({**common, 'situacao': 'necessita_documentos',
                          'explicacao_simples': 'O alerta exige conferir os documentos do processo.',
                          'proxima_diligencia': 'Solicitar os atestes e o processo integral.'})
    return {'itens': items}


class AgentReviewTests(unittest.TestCase):
    def test_catalog_limits_long_sources_and_resolution_preserves_exact_text(self):
        text = ''.join(f'Cláusula {i:03d}: condições publicadas. ' for i in range(100))
        dossiers = build_dossiers([{'Objeto': text}, {'Objeto': 'Outro contrato com evidência diferente.'}], audit_for(2))
        catalog = citation_catalog(dossiers[0])
        self.assertGreater(len(catalog), 1)
        self.assertTrue(all(8 <= len(pair['trecho']) <= 700 and pair['trecho'] in text for pair in catalog.values()))
        output = response('investigacao', dossiers)
        for item, dossier in zip(output['itens'], dossiers):
            item['evidencias'] = [{'citacao_id': next(iter(citation_catalog(dossier)))}]
        accepted = validate_stage('investigacao', output, dossiers)
        self.assertEqual(accepted['itens'][0]['evidencias'][0], next(iter(catalog.values())))
        for kind in ('unknown', 'other_line', 'extra_text'):
            bad = copy.deepcopy(output)
            ref = bad['itens'][0]['evidencias'][0]
            if kind == 'unknown': ref['citacao_id'] = 'inventado'
            elif kind == 'other_line': ref['citacao_id'] = next(iter(citation_catalog(dossiers[1])))
            else: ref['trecho'] = 'Texto acrescentado pelo modelo'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_stage('investigacao', bad, dossiers)

    def test_reviewer_catalog_contains_only_investigator_approved_pairs(self):
        dossiers = build_dossiers([{'Objeto': 'Serviços com escopo para conferência.', 'Valor': 'R$ 0.00'}], audit_for())
        previous = response('investigacao', dossiers)
        catalog = citation_catalog(dossiers[0], previous)
        self.assertEqual(list(catalog.values()), previous['itens'][0]['evidencias'])
        review = response('revisao', dossiers, previous)
        review['itens'][0]['evidencias'] = [{'citacao_id': next(iter(catalog))}]
        validate_stage('revisao', review, dossiers, previous)
        unapproved = next(identifier for identifier in citation_catalog(dossiers[0]) if identifier not in catalog)
        review['itens'][0]['evidencias'] = [{'citacao_id': unapproved}]
        with self.assertRaises(ValueError): validate_stage('revisao', review, dossiers, previous)

    def test_choice_workflow_resolves_both_stages_and_publishes_existing_frontend_format(self):
        def worker(llm, stage, batch, skills, previous, feedback):
            result = response(stage, batch, previous)
            for item, dossier in zip(result['itens'], batch):
                item['evidencias'] = [{'citacao_id': next(iter(citation_catalog(dossier, previous)))}]
            return '```json\n'+json.dumps(result)+'\n```'
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_review(self.folder(directory), worker=worker)
            self.assertEqual(result['status'], 'concluida')
            self.assertEqual(result['chamadas_nesta_execucao'], 2)
            evidence = result['itens'][0]['evidencias'][0]
            self.assertIn('fonte_id', evidence); self.assertIn('trecho', evidence); self.assertNotIn('citacao_id', evidence)

    def test_compatible_policy_checkpoint_is_revalidated_and_reused_without_calls(self):
        from src.batch_pipeline import fingerprint, write_json
        from src.agent_skills import skills_digest
        from src.agent_review import COMPATIBLE_POLICIES
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            batch = build_dossiers(self.records, self.audit)
            previous = None
            old_policy, old_prompt = COMPATIBLE_POLICIES[0]
            for stage in ('investigacao', 'revisao'):
                output = response(stage, batch, previous)
                signature = fingerprint({'dossies': batch, 'skills': skills_digest(load_skills()), 'modelo': self.llm.model,
                    'politica': old_policy, 'prompt': old_prompt, 'etapa': stage, 'investigacao': previous})
                write_json(folder / 'agentes/0001' / f'{stage}.json', {'assinatura': signature, 'saida': output})
                previous = output
            result = self.run_review(folder, wait=Mock(side_effect=AssertionError('Não pode esperar')))
            self.assertEqual(result['etapas_recuperadas'], 2)
            self.assertEqual(result['etapas_migradas'], 2)
            self.worker.assert_not_called()
            self.assertEqual(result['status'], 'concluida')
            self.records[0]['Valor do Contrato'] = 'R$ 1.00'
            self.run_review(folder)
            self.assertEqual(self.worker.call_count, 2)

    def test_json_plain_or_single_markdown_wrapper_preserves_values_and_quotes(self):
        data = {'itens': [{'trecho': 'R$ 0,00, ponto . e ``` dentro da citação'}]}
        raw = json.dumps(data, ensure_ascii=False)
        for value in (raw, '\ufeff'+raw, '```json\n'+raw+'\n```', '```JSON\r\n'+raw+'\r\n```', '```\n'+raw+'\n```'):
            with self.subTest(value=value[:10]):
                self.assertEqual(parse_stage_response(value), data)
        self.assertEqual(parse_stage_response(data), data)

    def test_parser_rejects_prose_multiple_objects_bad_fences_and_duplicate_keys(self):
        for value in ('', 'Aqui está: {"itens":[]}', '{"itens":[]} outra coisa', '{"itens":[]} {"itens":[]}',
                      '```json\n{}\n```\ntexto', '```python\n{}\n```', '```json\n{}',
                      '{"itens":[],"itens":[1]}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_stage_response(value)

    def test_fenced_responses_complete_both_stages_without_retry_and_still_validate_citations(self):
        def worker(llm, stage, batch, skills, previous, feedback):
            return '```json\n' + json.dumps(response(stage, batch, previous)) + '\n```'
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            result = self.run_review(folder, worker=worker)
            self.assertEqual(result['status'], 'concluida')
            self.assertEqual(result['chamadas_nesta_execucao'], 2)
            self.assertFalse((folder / 'agentes/0001/rejeicoes').exists())
        dossiers = build_dossiers(self.records, self.audit)
        bad = response('investigacao', dossiers)
        bad['itens'][0]['evidencias'][0]['trecho'] = 'Pagamento comprovado sem fonte'
        with self.assertRaisesRegex(ValueError, 'não literal'):
            validate_stage('investigacao', parse_stage_response('```json\n'+json.dumps(bad)+'\n```'), dossiers)

    def test_real_crew_transport_preserves_raw_short_field_for_our_validator_without_provider_call(self):
        from crewai import LLM
        llm = LLM(model='openai/gpt-4o-mini', api_key='test-only')
        dossiers = build_dossiers([{'Valor': 'R$ 0,00'}], audit_for())
        raw = json.dumps({'itens': [{'linha': 1, 'observacao': 'Valor publicado no portal.',
            'limite': 'Não comprova irregularidade.', 'evidencias': [{'fonte_id': dossiers[0]['fontes'][0]['id'], 'trecho': 'R$ 0,00'}]}]})
        with patch.object(type(llm), 'call', return_value='Final Answer: ' + raw) as provider:
            received = specialist_worker(llm, 'investigacao', dossiers, load_skills())
        self.assertEqual(received, raw)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(validate_stage('investigacao', json.loads(received), dossiers)['itens'][0]['evidencias'][0]['trecho'], 'R$ 0,00')

    def test_short_value_requires_complete_exact_untruncated_field_and_same_line(self):
        records = [{'Valor': 'R$ 0,00'}, {'Valor': 'R$ 0.00'}]
        dossiers = build_dossiers(records, audit_for(2))
        items = response('investigacao', dossiers)
        for item, dossier in zip(items['itens'], dossiers):
            source = next(s for s in dossier['fontes'] if s['tipo'] == 'campo_portal')
            item['evidencias'] = [{'fonte_id': source['id'], 'trecho': source['texto']}]
        accepted = validate_stage('investigacao', items, dossiers)
        self.assertEqual(accepted['itens'][0]['evidencias'][0]['trecho'], 'R$ 0,00')
        for kind in ('partial', 'format', 'wrong_line', 'document', 'truncated', 'empty'):
            changed, sources = copy.deepcopy(items), copy.deepcopy(dossiers)
            evidence = changed['itens'][0]['evidencias'][0]
            field = sources[0]['fontes'][0]
            if kind == 'partial': evidence['trecho'] = '0,00'
            elif kind == 'format': evidence['trecho'] = 'R$ 0.00'
            elif kind == 'wrong_line': evidence['fonte_id'] = sources[1]['fontes'][0]['id']
            elif kind == 'document': field['tipo'] = 'anexo_portal'
            elif kind == 'truncated': field['truncado'] = True
            else: evidence['trecho'] = ''
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_stage('investigacao', changed, sources)

    def test_short_field_can_be_reused_by_reviewer_but_other_pairs_are_rejected(self):
        dossiers = build_dossiers([{'Valor': 'R$ 0,00', 'Ano': '2026'}], audit_for())
        item = {'linha': 1, 'observacao': 'Valor publicado.', 'limite': 'Não comprova irregularidade.',
                'evidencias': [{'fonte_id': dossiers[0]['fontes'][0]['id'], 'trecho': 'R$ 0,00'}]}
        previous = validate_stage('investigacao', {'itens': [item]}, dossiers)
        review = response('revisao', dossiers, previous)
        validate_stage('revisao', review, dossiers, previous)
        changed = copy.deepcopy(review)
        changed['itens'][0]['evidencias'] = [{'fonte_id': dossiers[0]['fontes'][1]['id'], 'trecho': '2026'}]
        with self.assertRaisesRegex(ValueError, 'validadas'):
            validate_stage('revisao', changed, dossiers, previous)

    def test_raw_invalid_json_is_preserved_and_retry_uses_exact_current_field_examples(self):
        self.records = [{'Objeto': 'Objeto de cooperação técnica.', 'Valor': 'R$ 0.00'}]
        def worker(llm, stage, batch, skills, previous, feedback):
            if stage == 'investigacao' and not feedback:
                return 'resposta fora do JSON'
            if stage == 'investigacao':
                self.assertIn('R$ 0.00', feedback)
                self.assertIn('Não reescreva moedas', feedback)
            return response(stage, batch, previous)
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            result = self.run_review(folder, worker=worker)
            self.assertEqual(result['status'], 'concluida')
            rejection = json.loads(next((folder / 'agentes/0001/rejeicoes').glob('*.json')).read_text(encoding='utf-8'))
            self.assertEqual(rejection['resposta_original'], 'resposta fora do JSON')
            self.assertEqual(result['chamadas_nesta_execucao'], 3)

    def test_feedback_for_reviewer_only_contains_pairs_accepted_by_investigator(self):
        dossiers = build_dossiers(self.records, self.audit)
        previous = response('investigacao', dossiers)
        feedback = validation_feedback(ValueError('Citação inválida'), dossiers, previous)
        self.assertIn(previous['itens'][0]['evidencias'][0]['trecho'], feedback)
        self.assertNotIn('R$ 10579129.21', feedback)

    def test_wait_and_call_phases_are_saved_before_operation_and_cleared_at_end(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            seen = []
            def wait(seconds):
                if seconds:
                    saved = json.loads((folder / 'revisao_agentes.json').read_text(encoding='utf-8'))
                    self.assertEqual(saved['fase_atual'], 'aguardando_intervalo')
                    self.assertIn('espera_ate', saved)
                    self.assertEqual(saved['lote_atual'], 1)
                    seen.append('espera')
            def worker(llm, stage, batch, skills, previous, feedback):
                saved = json.loads((folder / 'revisao_agentes.json').read_text(encoding='utf-8'))
                self.assertEqual(saved['fase_atual'], 'chamando_ia')
                self.assertNotIn('espera_ate', saved)
                seen.append(stage)
                return response(stage, batch, previous)
            result = review_saved_audit(self.llm, folder, self.records, self.audit,
                ReviewSettings(interval_seconds=65), worker=worker, wait=wait)
            self.assertEqual(result['fase_atual'], 'concluida')
            self.assertNotIn('espera_ate', result)
            self.assertIn('espera', seen)
            self.assertIn('investigacao', seen)
            self.assertIn('revisao', seen)

    def test_extracted_annexes_enter_dossier_only_for_matching_record_and_invalidate_review(self):
        from src.documents import digest
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            doc = {'id': 'a'*64, 'status': 'lido', 'sha256': 'b'*64, 'rotulo': 'Ficha do portal',
                   'tipo_documento': 'ficha_portal', 'url': 'https://transparencia.marica.rj.gov.br/a.pdf',
                   'paginas': [{'pagina': 1, 'texto': 'Documento com evidência literal para revisão.', 'metodo': 'texto_pdf',
                                'qualidade': 'texto_extraido_nao_validado', 'aviso': None, 'truncado': False}]}
            manifest = {'assinatura': 'v1', 'consultas': [{'linha': 1, 'registro_sha256': digest(self.records[0]),
                        'assinatura': 'line-v1', 'documentos': [doc]}]}
            path = folder / 'documentos.json'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            dossiers = build_dossiers(self.records, self.audit, documents=manifest)
            source = next(s for s in dossiers[0]['fontes'] if s['tipo'] == 'anexo_portal')
            self.assertIn('Ficha cadastral', source['rotulo'])
            self.assertEqual(source['pagina'], 1)
            first = self.run_review(folder, wait=lambda _: None)
            self.assertEqual(first['documentos_assinatura'], 'v1')
            calls = self.worker.call_count
            self.run_review(folder, wait=Mock(side_effect=AssertionError('Sem espera no cache')))
            self.assertEqual(self.worker.call_count, calls)
            manifest['assinatura'] = 'v2'
            manifest['consultas'][0]['assinatura'] = 'line-v2'
            doc['paginas'][0]['texto'] = 'Documento alterado com evidência literal nova.'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            self.run_review(folder, wait=lambda _: None)
            self.assertGreater(self.worker.call_count, calls)
            stale = build_dossiers([{'Objeto': 'Outro registro'}], self.audit, documents=manifest)
            self.assertFalse(any(s['tipo'] == 'anexo_portal' for s in stale[0]['fontes']))

    def setUp(self):
        self.records = [{'Detalhe - Objeto': 'Reconhecimento de dívida por serviços sem cobertura contratual.',
                         'Valor do Contrato': 'R$ 10579129.21', 'URL do contrato':
                         'https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao/1/visualizar'}]
        self.audit = audit_for()
        self.settings = ReviewSettings(interval_seconds=0)
        self.llm = SimpleNamespace(model='test-model')
        self.worker = Mock(side_effect=lambda llm, stage, batch, skills, previous, feedback:
                           response(stage, batch, previous))

    def folder(self, directory):
        folder = Path(directory)
        (folder / 'parecer.json').write_text(self.audit.model_dump_json(), encoding='utf-8')
        return folder

    def run_review(self, folder, **kwargs):
        return review_saved_audit(self.llm, folder, self.records, self.audit, self.settings,
                                  worker=kwargs.pop('worker', self.worker), **kwargs)

    def test_conditional_skills_are_local_and_do_not_create_findings(self):
        self.assertIn('cobertura_contratual', select_skills(self.records[0], ['Conferir']))
        self.assertNotIn('atas', select_skills({}, ['Conferir objeto']))
        self.assertIn('atas', select_skills({}, ['Ata anulada; verificar origem']))
        self.assertIn('precos_e_escopo', select_skills({}, ['Conferir preços e quantitativos']))
        self.assertEqual(set(load_skills()), {'documental', 'revisao', 'atas', 'cobertura_contratual', 'precos_e_escopo'})

    def test_dossiers_exclude_annex_links_and_reject_unofficial_pdf_sources(self):
        record = {**self.records[0], 'Links publicados nos detalhes': '[{"url":"https://example.org/x.pdf"}]'}
        gazette = {'consultas': [{'linha': 1, 'resultados': [
            {'url_pdf': 'https://example.org/x.pdf', 'edicao': 'Falsa', 'trecho': 'Não ler', 'pagina': 1}]}]}
        dossier = build_dossiers([record], self.audit, gazette)[0]
        self.assertTrue(all(s['tipo'] != 'publicacao_candidata' for s in dossier['fontes']))
        self.assertFalse(any(s['rotulo'] == 'Links publicados nos detalhes' for s in dossier['fontes']))
        self.assertEqual(dossier['diario']['referencias_nao_incluidas'], 1)

    def test_field_truncation_and_gazette_omissions_are_explicit(self):
        settings = ReviewSettings(max_field_chars=20, max_hits=1)
        hit = {'url_pdf': 'https://www.marica.rj.gov.br/x.pdf', 'edicao': 'DOM teste',
               'trecho': 'Publicação candidata sem prova automática.', 'pagina': 2, 'coluna': 1}
        gazette = {'status': 'consulta_parcial', 'consultas': [{'linha': 1, 'resultados': [hit, hit]}]}
        dossier = build_dossiers(self.records, self.audit, gazette, settings)[0]
        self.assertTrue(dossier['fontes'][0]['truncado'])
        self.assertEqual(len(dossier['fontes'][0]['texto']), 20)
        self.assertEqual(dossier['diario']['referencias_nao_incluidas'], 1)
        self.assertEqual(dossier['fontes'][-1]['pagina'], 2)

    def test_global_lines_and_literal_quotes_cannot_be_fabricated_or_crossed(self):
        records = [*self.records, {'Objeto': 'Serviços de manutenção de outro contrato.'}]
        dossiers = build_dossiers(records, audit_for(2))
        valid = response('investigacao', dossiers)
        self.assertEqual(len(validate_stage('investigacao', valid, dossiers)['itens']), 2)
        for mutation in ('quote', 'source', 'duplicate', 'missing'):
            bad = copy.deepcopy(valid)
            if mutation == 'quote':
                bad['itens'][0]['evidencias'][0]['trecho'] = 'Pagamento comprovado sem fonte'
            elif mutation == 'source':
                bad['itens'][0]['evidencias'][0] = valid['itens'][1]['evidencias'][0]
            elif mutation == 'duplicate':
                bad['itens'][1]['linha'] = 1
            else:
                bad['itens'].pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_stage('investigacao', bad, dossiers)

    def test_reviewer_cannot_add_quote_not_checked_by_investigator(self):
        dossiers = build_dossiers(self.records, self.audit)
        previous = response('investigacao', dossiers)
        review = response('revisao', dossiers, previous)
        review['itens'][0]['evidencias'][0]['trecho'] = dossiers[0]['fontes'][0]['texto'][5:35]
        # response shares the previous reference, so restore the original separately.
        previous = response('investigacao', dossiers)
        with self.assertRaisesRegex(ValueError, 'validadas'):
            validate_stage('revisao', review, dossiers, previous)

    def test_resume_reuses_investigation_after_review_failure(self):
        def interrupted(llm, stage, batch, skills, previous, feedback):
            if stage == 'revisao':
                raise RuntimeError('429 quota per day')
            return response(stage, batch, previous)
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            first = self.run_review(folder, worker=Mock(side_effect=interrupted), wait=Mock())
            self.assertEqual(first['status'], 'interrompida')
            self.assertEqual(first['itens'], [])
            result = self.run_review(folder)
            self.assertEqual(result['status'], 'concluida')
            self.assertEqual(result['etapas_recuperadas'], 1)
            self.assertEqual(self.worker.call_count, 1)
            self.assertEqual(self.worker.call_args.args[1], 'revisao')
            saved = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
            self.assertEqual(saved.suspeitos, self.audit.suspeitos)
            self.assertEqual(saved.linhas_analisadas, self.audit.linhas_analisadas)
            again = self.run_review(folder)
            self.assertEqual(again['etapas_recuperadas'], 2)
            self.assertEqual(self.worker.call_count, 1)
            self.assertEqual((folder / 'relatorio.md').read_text(encoding='utf-8').count('<!-- revisao-agentes:inicio -->'), 1)

    def test_source_model_and_skill_changes_invalidate_only_review_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            original_checkpoint = folder / 'lotes' / '0001' / 'checkpoint.json'
            original_checkpoint.parent.mkdir(parents=True)
            original_checkpoint.write_text('{"historico":true}')
            self.run_review(folder)
            self.worker.reset_mock()
            self.records[0]['Valor do Contrato'] = 'R$ 1.00'
            self.run_review(folder)
            self.assertEqual(self.worker.call_count, 2)
            self.llm.model = 'other-model'
            self.worker.reset_mock()
            self.run_review(folder)
            self.assertEqual(self.worker.call_count, 2)
            self.worker.reset_mock()
            skills = load_skills(); skills['revisao'] += '\nConferir novamente.'
            with patch('src.agent_review.load_skills', return_value=skills):
                self.run_review(folder)
            self.assertEqual(self.worker.call_count, 2)
            self.assertEqual(original_checkpoint.read_text(), '{"historico":true}')

    def test_validation_failure_preserves_raw_and_supplies_feedback(self):
        def worker(llm, stage, batch, skills, previous, feedback):
            if stage == 'investigacao' and not feedback:
                return '{"itens":[]}'
            return response(stage, batch, previous)
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            result = self.run_review(folder, worker=Mock(side_effect=worker))
            self.assertEqual(result['status'], 'concluida')
            rejections = list((folder / 'agentes' / '0001' / 'rejeicoes').glob('*.json'))
            self.assertEqual(len(rejections), 1)
            self.assertEqual(json.loads(rejections[0].read_text(encoding='utf-8'))['resposta_original'], '{"itens":[]}')

    def test_retry_after_minute_quota_and_stop_on_daily_limit(self):
        worker = Mock(side_effect=[RuntimeError("429 {'retryDelay': '95s'}"),
                                  response('investigacao', build_dossiers(self.records, self.audit)),
                                  RuntimeError('429 daily quota')])
        with tempfile.TemporaryDirectory() as directory:
            wait = Mock()
            result = self.run_review(self.folder(directory), worker=worker, wait=wait)
            self.assertEqual(result['status'], 'interrompida')
            self.assertEqual(worker.call_count, 3)
            self.assertIn(97, [c.args[0] for c in wait.call_args_list])

    def test_no_findings_does_not_call_llm_or_wait(self):
        self.audit.suspeitos = []
        with tempfile.TemporaryDirectory() as directory:
            wait = Mock()
            result = self.run_review(self.folder(directory), wait=wait)
            self.assertEqual(result['status'], 'sem_achados')
            self.worker.assert_not_called()
            wait.assert_not_called()

    def test_batch_size_and_bytes_are_bounded_without_omitting_findings(self):
        dossiers = build_dossiers(self.records * 4, audit_for(4))
        batches = split_dossiers(dossiers, ReviewSettings(max_records=2))
        self.assertEqual([d['linha'] for b in batches for d in b], [1, 2, 3, 4])
        self.assertTrue(all(len(b) <= 2 for b in batches))
        with self.assertRaisesRegex(ValueError, 'excede'):
            split_dossiers(dossiers, ReviewSettings(max_bytes=10))

    def test_planning_is_local_and_does_not_require_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'data' / 'reports' / 'run1'
            folder.mkdir(parents=True)
            self.folder(folder)
            (folder / 'contratos.json').write_text(json.dumps(self.records), encoding='utf-8')
            with patch('src.config.ROOT', root), patch('src.main.create_audit_llm') as llm:
                self.assertEqual(main(['--planejar', '--execucao', 'run1']), 0)
                llm.assert_not_called()
            self.assertFalse((folder / 'revisao_agentes.json').exists())

    def test_specialist_uses_only_current_batch_and_disables_delegation(self):
        from crewai import LLM
        llm = LLM(model='openai/gpt-4o-mini', api_key='test-only')
        dossiers = build_dossiers(self.records, self.audit)
        with patch('src.agent_review.Crew') as crew:
            crew.return_value.kickoff.return_value.raw = json.dumps(response('investigacao', dossiers))
            specialist_worker(llm, 'investigacao', dossiers, load_skills())
            task = crew.call_args.kwargs['tasks'][0]
            self.assertFalse(task.agent.allow_delegation)
            self.assertEqual(task.agent.tools, [])
            self.assertEqual(task.agent.max_retry_limit, 0)
            self.assertIn('DOSSIÊ', task.description)
            self.assertIn('ESQUEMA JSON', task.description)
            self.assertIsNone(task.output_pydantic)
            self.assertIsNone(task.output_json)

    def test_additional_review_failure_does_not_block_archive(self):
        from src.batch_pipeline import run_pipeline, BatchSettings
        with tempfile.TemporaryDirectory() as directory:
            folder = self.folder(directory)
            (folder / 'contratos.json').write_text(json.dumps(self.records), encoding='utf-8')
            (folder / 'progresso.json').write_text('{"status":"analise_concluida"}')
            with patch.dict(os.environ, {'GAZETTE_ENABLED': 'false', 'REVIEW_AGENTS_ENABLED': 'true'}), \
                 patch('src.batch_pipeline.audit_in_batches'), \
                 patch('src.agent_review.review_saved_audit', side_effect=RuntimeError('Indisponível')), \
                 patch('src.batch_pipeline.ArquivarContratosTool') as archive:
                archive.return_value._run.return_value = '{"ok":true,"inseridos":1}'
                self.assertTrue(run_pipeline(self.llm, folder, BatchSettings(), resume=True)['ok'])
            result = json.loads((folder / 'revisao_agentes.json').read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'interrompida')
            self.assertEqual(result['itens'], [])
            self.assertEqual(json.loads((folder / 'progresso.json').read_text())['status'], 'concluido')
