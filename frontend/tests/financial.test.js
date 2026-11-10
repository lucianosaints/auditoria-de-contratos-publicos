import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { readFinancial } from '../server/financial.js';
import { financialEntries, financialUrl } from '../src/financial.js';

test('financeiro rejeita resultado obsoleto, duplicação de linhas e URLs externas', () => {
  const data = { records: [{}], financialCurrent: true, financial: { versao: 1, politica_identidade: 2, limite: 'Limites', linhas: [1], configuracao: {}, processados: 1, detalhes_consultados: 0, consultas_fornecedores: [],
    consultas: [{ linha: 1, vinculos: [] }] } };
  assert.equal(financialEntries(data).length, 1);
  assert.equal(financialEntries({ ...data, financialCurrent: false }), null);
  assert.equal(financialEntries({ ...data, financial: { ...data.financial, politica_identidade: 1 } }), null);
  assert.equal(financialEntries({ ...data, id: 'importado' }), null);
  assert.equal(financialEntries({ ...data, financial: { ...data.financial, consultas: [...data.financial.consultas, ...data.financial.consultas] } }), null);
  assert.ok(financialUrl('https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao/26417/empenho'));
  for (const url of ['https://evil.test/a', 'javascript:alert(1)', 'https://u:p@transparencia.marica.rj.gov.br/e-cidade/contratos/padrao/26417/empenho']) assert.equal(financialUrl(url), null);
});

test('servidor confere coleta, parecer, HTML e assinatura financeira', async t => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'audit-financial-'));
  t.after(async () => { assert.equal(path.dirname(folder), path.resolve(os.tmpdir())); assert.ok(path.basename(folder).startsWith('audit-financial-')); await rm(folder, { recursive: true, force: true }); });
  const hash = v => createHash('sha256').update(v).digest('hex');
  await writeFile(path.join(folder, 'contratos.json'), '[]');
  await writeFile(path.join(folder, 'parecer.json'), '{}');
  await writeFile(path.join(folder, 'source.html'), 'original');
  const body = { coleta_sha256: hash('[]'), fontes_html: [{ arquivo: 'source.html', sha256: hash('original') }], parecer_sha256: hash('{}'), politica_identidade: 2, versao: 1 };
  const value = { ...body, assinatura: hash(JSON.stringify(body)) };
  await writeFile(path.join(folder, 'financeiro.json'), JSON.stringify(value));
  assert.equal((await readFinancial(folder)).financialCurrent, true);
  await writeFile(path.join(folder, 'source.html'), 'mudou');
  assert.equal((await readFinancial(folder)).financialCurrent, false);
  await writeFile(path.join(folder, 'source.html'), 'original');
  await writeFile(path.join(folder, 'parecer.json'), '{"mudou":true}');
  assert.equal((await readFinancial(folder)).financialCurrent, false);
});
