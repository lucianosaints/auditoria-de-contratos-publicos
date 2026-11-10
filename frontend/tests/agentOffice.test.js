import test from 'node:test';
import assert from 'node:assert/strict';
import { officeState, officeTransitions } from '../src/agentOffice.js';
const data = { id: 'run', progress: { status: 'analisando' } };
const job = { id: 'job', run_id: 'run', active: true, action: 'nova_auditoria' };
test('escritório só anima etapa confirmada da execução conectada', () => {
  assert.equal(officeState(data, job, true).index, 1);
  assert.equal(officeState(data, job, false).moving, false);
  assert.equal(officeState(data, { ...job, run_id: 'other' }, true).index, -1);
  assert.equal(officeState(data, { ...job, active: false }, true).moving, false);
  assert.equal(officeState({ ...data, progress: null }, job, true).index, -1);
});
test('entregas preservam mudanças rápidas sem duplicação ou repetição de histórico', () => {
  let current = { ...job, office: { agent: 0, events: [] } };
  let result = officeTransitions({ key: '' }, current, 'run');
  current.office.events = [0,1,3,4,2].map((agent, i) => ({ agent, seq: i+1 }));
  result = officeTransitions(result.cursor, current, 'run');
  assert.deepEqual(result.deliveries.map(e => [e.from,e.to]), [[0,1],[1,3],[3,4],[4,2]]);
  assert.equal(officeTransitions(result.cursor, current, 'run').deliveries.length, 0);
  assert.equal(officeTransitions({ key: '' }, current, 'run').deliveries.length, 0);
  assert.equal(officeTransitions(result.cursor, { ...current, active: false, status: 'falhou' }, 'run').reset, true);
  assert.equal(officeTransitions(result.cursor, current, 'other').reset, true);
});
test('telemetria do job prevalece sobre arquivo antigo e respeita pausa', () => {
  assert.equal(officeState(data, { ...job, office: { agent: 0 } }, true).index, 0);
  assert.equal(officeState(data, { ...job, office: { agent: 2 } }, true).index, 2);
  assert.equal(officeState(data, { ...job, office: { agent: 4, phase: 'aguardando_cota' } }, true).moving, false);
  assert.equal(officeState(data, { ...job, office: { agent: null } }, true).index, -1);
});
test('revisão e pausas usam a etapa adicional sem herdar a auditoria', () => {
  const review = { ...data, review: { etapa_atual: 'revisao', fase_atual: 'aguardando_cota' } };
  const state = officeState(review, { ...job, action: 'revisar_achados' }, true);
  assert.equal(state.index, 4);
  assert.equal(state.moving, false);
  assert.equal(officeState(data, { ...job, status: 'parando' }, true).moving, false);
});
