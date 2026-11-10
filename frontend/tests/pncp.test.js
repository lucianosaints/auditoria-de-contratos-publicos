import test from 'node:test';
import assert from 'node:assert/strict';
import { pncpEntries, pncpUrl, validatePncp } from '../src/pncp.js';
import { executionStatus } from '../src/executionStatus.js';

test('vínculos PNCP são ocultados quando registro ou seleção de alertas muda', () => {
  const record = { Objeto: 'Exemplo', Valor: '10' };
  const data = { records: [record], audit: { suspeitos: [{ linha: 1 }] }, pncp: { versao: 1, linhas: [1], consultas: [
    { linha: 1, registro_original: { Valor: '10', Objeto: 'Exemplo' }, situacao: 'confirmado_por_regras', candidatos: [], documentos: [] }] } };
  assert.equal(pncpEntries(data).length, 1);
  assert.equal(pncpEntries({ ...data, records: [{ ...record, Valor: '20' }] }).length, 0);
  assert.equal(pncpEntries({ ...data, audit: { suspeitos: [] } }).length, 0);
});

test('links PNCP rejeitam origem falsa, credenciais e scripts', () => {
  assert.ok(pncpUrl('https://pncp.gov.br/app/contratos/1/2026/1'));
  for (const url of ['javascript:alert(1)', 'https://pncp.gov.br.evil.test/a', 'https://u:p@pncp.gov.br/a', 'http://pncp.gov.br/a']) {
    assert.equal(pncpUrl(url), null);
  }
});

test('importação malformada é rejeitada e progresso PNCP não herda lotes da auditoria', () => {
  assert.throws(() => validatePncp({ versao: 1, consultas: [null] }), /estrutura/);
  const result = executionStatus({ id: 'selected', records: [], progress: { lotes_concluidos: 32, total_lotes: 32 },
    pncp: { status: 'em_andamento', processados: 2, linhas: [1, 2, 3] } },
    { active: true, run_id: 'selected', action: 'consultar_pncp' }, true);
  assert.deepEqual(result.progress, { value: 2, total: 3 });
});
