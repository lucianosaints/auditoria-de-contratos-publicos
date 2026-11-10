import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildRows, moneyValue, safeUrl, validateDataset } from '../src/data.js';
import { buildSimpleSummary } from '../src/simpleSummary.js';

test('achados base 1 são agrupados sem atribuir índices inválidos a contratos', () => {
  const rows = buildRows({ records: [{ Processo: 'A' }, { Processo: 'B' }], audit: { suspeitos: [
    { linha: 0, motivo_suspeita: 'Inválido' }, { linha: 2, motivo_suspeita: 'Custos ausentes' },
    { linha: 2, motivo_suspeita: 'Custos ausentes' }, { linha: 3, motivo_suspeita: 'Inválido' },
  ] } });
  assert.equal(rows[0].flagged, false);
  assert.deepEqual(rows[1].reasons, ['Custos ausentes']);
  assert.equal(rows[1].category, 'Preços e custos');
});
test('valores ausentes e ambíguos não viram zero', () => {
  assert.equal(moneyValue('R$ 1.234,56'), 1234.56);
  assert.equal(moneyValue('1234.56'), 1234.56);
  assert.equal(moneyValue('0,00'), 0);
  for (const input of ['', '1.234', '12.34,56', 'NaN', '1e4']) assert.equal(moneyValue(input), null);
});
test('links externos não podem executar JavaScript ou embutir credenciais', () => {
  assert.equal(safeUrl('javascript:alert(1)'), null);
  assert.equal(safeUrl('https://user:pass@example.org'), null);
  assert.equal(safeUrl('https://example.org/contrato'), 'https://example.org/contrato');
});
test('importação valida formato dos registros e índices dos achados', () => {
  assert.throws(() => validateDataset({ records: [{ valor: null }] }));
  assert.throws(() => validateDataset({ records: [], audit: { suspeitos: [{ linha: '1', motivo_suspeita: 'x' }], linhas_analisadas: [], relatorio_markdown: '' } }));
  assert.doesNotThrow(() => validateDataset({ records: [{ Valor: 'R$ 0,00' }], audit: null }));
});

test('resumo simples distingue reconhecimento de dívida de pagamento', () => {
  const record = { 'Detalhe - Objeto': 'O município reconhece serviços sem cobertura contratual para indenização.',
    'Valor do Contrato': 'R$ 10579129.21', 'Detalhe - Processo': '20857/2025' };
  const summary = buildSimpleSummary(record, ['Conferir dívida reconhecida']);
  assert.equal(summary.tipo, 'sem_cobertura');
  assert.ok(summary.em_resumo.includes('R$ 10.579.129,21'));
  assert.ok(summary.significado_pratico.includes('não comprova que ela já foi paga'));
  assert.ok(summary.proxima_diligencia.includes('20857/2025'));
  assert.equal(buildSimpleSummary(record, []), null);
});

test('resumo não confirma sobrepreço nem converte dado ausente em zero', () => {
  const summary = buildSimpleSummary({ Valor: '100,00' }, ['Sobrepreço não verificável']);
  assert.equal(summary.tipo, 'precos');
  assert.ok(summary.significado_pratico.includes('não se pode afirmar sobrepreço'));
  assert.notEqual(buildSimpleSummary({ Valor: '' }, ['Valor zerado']).tipo, 'valor_zero');
});

test('consulta documental importada rejeita resultados que não podem ser exibidos', () => {
  assert.throws(() => validateDataset({ records: [], gazette: { consultas: [null] } }));
  assert.doesNotThrow(() => validateDataset({ records: [], gazette: {
    limite: 'Consulta parcial', edicoes_lidas: 0, consultas: [], status: 'consulta_indisponivel',
  } }));
});
