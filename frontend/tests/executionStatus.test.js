import { test } from 'node:test';
import assert from 'node:assert/strict';
import { elapsedTime, executionStatus, failureExplanation } from '../src/executionStatus.js';

const data = { id: 'selected', records: [{ Objeto: 'Teste' }], progress: { status: 'concluido', total_lotes: 32, lotes_concluidos: 32, linhas_concluidas: 450 },
  receipt: { ok: true, recebidos: 94 }, review: { status: 'interrompida', erro: 'String should have at least 8 characters', total_contratos: 94, total_lotes: 19, lotes_concluidos: 0, itens: [] } };

test('auditoria concluída e revisão falha aparecem separadamente, sem indicar trabalho ativo', () => {
  const state = executionStatus(data, { run_id: 'selected', action: 'revisar_achados', status: 'falhou', active: false }, true);
  assert.equal(state.title, 'Nenhuma ação em andamento');
  assert.ok(state.details.some(t => t.includes('450 contratos') && t.includes('32/32') && t.includes('94 contratos arquivados')));
  assert.match(state.failure, /citação curta sem o campo completo/);
  assert.equal(state.progress, null);
  assert.ok(state.details.some(t => t.includes('Revisão adicional interrompida: 0/94')));
});

test('revisão ativa mostra progresso próprio, etapa, pausa e prazo sem herdar 32 lotes da auditoria', () => {
  const active = { ...data, review: { ...data.review, status: 'em_andamento', fase_atual: 'aguardando_intervalo', espera_ate: '2026-10-21T00:30:00Z', etapa_atual: 'investigacao', lote_atual: 1 } };
  const state = executionStatus(active, { run_id: 'selected', action: 'revisar_achados', active: true }, true);
  assert.match(state.title, /em andamento/);
  assert.deepEqual(state.progress, { value: 0, total: 19 });
  assert.ok(state.details.some(t => t.includes('Investigador') && t.includes('lote atual 1')));
  assert.equal(state.waitUntil, active.review.espera_ate);
  assert.equal(state.failure, null);
});

test('perda de conexão não afirma que não há trabalho e outra execução não usa progresso da seleção', () => {
  const job = { run_id: 'other', action: 'nova_auditoria', active: true };
  const state = executionStatus(data, job, true);
  assert.ok(state.details.some(t => t.includes('outra execução')));
  assert.equal(state.progress, null);
  assert.match(executionStatus(data, job, false).title, /Não foi possível confirmar/);
});

test('contagem de documentos e interrupção são identificadas', () => {
  const docs = { ...data, documents: { documentos_processados: 4, planejamento: { documentos: 195 } } };
  const state = executionStatus(docs, { run_id: 'selected', action: 'coletar_documentos', status: 'parando', active: true }, true);
  assert.match(state.title, /Interrupção solicitada/);
  assert.deepEqual(state.progress, { value: 4, total: 195 });
});

test('nova consulta financeira não herda contadores do resultado anterior', () => {
  const job = { run_id: 'selected', action: 'consultar_financeiro', active: true };
  const previous = { ...data, review: null, financialCurrent: true,
    financial: { status: 'concluida_com_limites', processados: 94, linhas: Array.from({length: 94}, (_, i) => i + 1) } };
  const state = executionStatus(previous, job, true);
  assert.equal(state.progress, null);
  assert.ok(!state.details.some(t => t.startsWith('Financeiro: 94/94')));
  const active = executionStatus({ ...previous, financial: { ...previous.financial, status: 'em_andamento', processados: 3 } }, job, true);
  assert.deepEqual(active.progress, { value: 3, total: 94 });
});

test('erro é traduzido sem expor pilha ou dados da resposta, e tempo decorrido é legível', () => {
  assert.match(failureExplanation('Expecting value: line 1 column 1 (char 0)'), /JSON da resposta/);
  assert.match(failureExplanation('Resposta não é JSON válido'), /texto original foi preservado/);
  assert.match(failureExplanation('429 daily quota'), /limitou/);
  assert.match(failureExplanation('[WinError 5] Acesso negado: caminho privado'), /Windows impediu a gravação/);
  assert.ok(!failureExplanation('[WinError 32] caminho privado').includes('caminho privado'));
  assert.match(failureExplanation('Failed to validate structured output'), /validação/);
  assert.ok(!failureExplanation('erro com segredo').includes('segredo'));
  assert.equal(elapsedTime('2026-10-21T00:00:00Z', Date.parse('2026-10-21T00:02:05Z')), '2min 5s');
  assert.equal(elapsedTime('inválido', Date.now()), '');
});
