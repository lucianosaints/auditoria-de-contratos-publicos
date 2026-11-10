import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sourceCoverage, supportFor } from '../src/evidenceSupport.js';

test('cobertura conta fontes e páginas citadas sem duplicar citações nem inferir leitura integral', () => {
  const source = { id: 'L1-R1', tipo: 'anexo_portal', documento_id: 'a', pagina: 9, metodo: 'ocr_windows', rag: true, tipo_documento: 'ficha_portal' };
  const item = { evidencias: [{ fonte_id: source.id, fonte: source }, { fonte_id: source.id, fonte: source },
    { fonte_id: 'L1-P1', fonte: { tipo: 'campo_portal' } }, { fonte_id: 'L1-D1', fonte: { tipo: 'publicacao_candidata', url: 'https://example.test/1.pdf', pagina: 2 } }] };
  const result = sourceCoverage(item, {});
  assert.equal(result.portal, 1); assert.equal(result.diario, 1); assert.equal(result.paginasDiario, 1);
  assert.equal(result.anexos, 1); assert.equal(result.paginasPdf, 1); assert.ok(result.ocr && result.ficha);
  assert.equal(result.rag, 'Trechos RAG citados');
  assert.match(sourceCoverage({ evidencias: [] }, { rag_transporte: 'mcp_stdio' }).rag, /nenhum trecho/);
  assert.match(sourceCoverage({ evidencias: [] }, { rag_transporte: null }).rag, /não utilizado/);
  assert.match(sourceCoverage({ evidencias: [] }, {}).rag, /sem registro/);
});

test('conferência só aparece para mesma revisão e mesmo item, sem sinal verde para interpretação', () => {
  const item = { linha: 1, explicacao_simples: 'Original', evidencias: [] };
  const checked = { linha: 1, revisao_original: structuredClone(item), status: 'sem_alertas_nas_regras', avisos: [] };
  const data = { review: { atualizado_em: 'v1' }, verification: { versao: 1, revisao_atualizado_em: 'v1', itens: [checked] } };
  assert.equal(supportFor(data, item), checked);
  assert.equal(supportFor(data, { ...item, explicacao_simples: 'Alterada' }), null);
  assert.equal(supportFor({ ...data, review: { atualizado_em: 'v2' } }, item), null);
  checked.avisos = [{ codigo: 'qa', trecho: 'Original', mensagem: 'Conferir.' }];
  assert.equal(supportFor(data, item), null);
  checked.status = 'conferir'; assert.equal(supportFor(data, item), checked);
  checked.avisos[0].mensagem = null; assert.equal(supportFor(data, item), null);
});
