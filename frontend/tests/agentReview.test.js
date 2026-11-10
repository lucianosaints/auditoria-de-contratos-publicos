import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reviewState, validateAgentReview } from '../src/agentReview.js';

const records = [{ Objeto: 'Serviços sem cobertura contratual.' }];
const audit = { suspeitos: [{ linha: 1, motivo_suspeita: 'Conferir período' }] };
function fixture() {
  return { status: 'concluida', total_contratos: 1, nota: 'Revisão automatizada.', itens: [{
    linha: 1, situacao: 'necessita_documentos', explicacao_simples: 'Solicitar os documentos.',
    limite: 'Não comprova pagamento.', proxima_diligencia: 'Conferir atestes.', skills: ['documental'],
    registro_original: records[0], motivos_originais: ['Conferir período'],
    evidencias: [{ fonte_id: 'L1-P1', trecho: 'sem cobertura contratual', fonte: { rotulo: 'Objeto', texto: records[0].Objeto } }],
  }] };
}

test('revisão compatível mantém citações e status sem alterar alertas', () => {
  const review = fixture();
  validateAgentReview(review);
  const state = reviewState({ records, audit, review });
  assert.equal(state.items.length, 1);
  assert.equal(audit.suspeitos[0].motivo_suspeita, 'Conferir período');
});

test('trocar coleta, motivos ou consulta do Diário oculta revisão desatualizada', () => {
  const review = fixture();
  assert.equal(reviewState({ records: [{ Objeto: 'Outro contrato' }], audit, review }).stale, 1);
  assert.equal(reviewState({ records, audit: { suspeitos: [] }, review }).items.length, 0);
  assert.equal(reviewState({ records, audit, review, gazette: { assinatura: 'nova' } }).items.length, 0);
});

test('importação rejeita estruturas ruins, citações inventadas, outra linha e duplicação', () => {
  for (const change of [
    r => { r.itens[0].evidencias[0].trecho = 'Frase inventada'; },
    r => { r.itens[0].evidencias[0].fonte_id = 'L2-P1'; },
    r => { r.itens[0].situacao = 'fraude_confirmada'; },
    r => { r.itens.push(r.itens[0]); },
    r => { r.itens[0].registro_original = null; },
  ]) {
    const review = fixture(); change(review);
    assert.throws(() => validateAgentReview(review));
  }
  assert.doesNotThrow(() => validateAgentReview({ status: 'interrompida', total_contratos: 1, itens: [], nota: 'Revisão interrompida.' }));
});

test('valor curto só é aceito se for o campo completo, literal e não truncado', () => {
  const review = fixture();
  const citation = review.itens[0].evidencias[0];
  citation.trecho = 'R$ 0,00';
  citation.fonte = { tipo: 'campo_portal', rotulo: 'Valor', texto: 'R$ 0,00', truncado: false };
  assert.doesNotThrow(() => validateAgentReview(review));
  for (const mutation of [
    r => { r.itens[0].evidencias[0].trecho = '0,00'; },
    r => { r.itens[0].evidencias[0].trecho = 'R$ 0.00'; },
    r => { r.itens[0].evidencias[0].fonte.tipo = 'anexo_portal'; },
    r => { r.itens[0].evidencias[0].fonte.truncado = true; },
  ]) {
    const changed = structuredClone(review); mutation(changed);
    assert.throws(() => validateAgentReview(changed));
  }
});
