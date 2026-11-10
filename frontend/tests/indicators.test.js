import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { readIndicators } from '../server/indicators.js';
import { exactBrl, indicatorState } from '../src/indicators.js';

test('valores grandes são apresentados sem arredondamento binário', () => {
  assert.equal(exactBrl('92233720368547758.10'), 'R$ 92.233.720.368.547.758,10');
  assert.equal(exactBrl('0.00'), 'R$ 0,00');
  assert.equal(exactBrl(null), 'Não informado');
  assert.equal(indicatorState({ id: 'selected', indicators: { versao: 1 }, indicatorsCurrent: false }), 'desatualizado');
});

test('servidor recusa indicadores quando fontes ou artefato mudam', async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'audit-indicators-'));
  t.after(async () => {
    assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('audit-indicators-'));
    await rm(root, { recursive: true, force: true });
  });
  const hash = x => createHash('sha256').update(x).digest('hex');
  const records = '[{"Objeto":"Exemplo"}]';
  await writeFile(path.join(root, 'contratos.json'), records);
  // Ordem canônica igual à serialização usada no Python.
  const body = { fontes_sha256: { 'contratos.json': hash(records), 'documentos.json': null,
    'parecer.json': null, 'pncp.json': null }, versao: 1 };
  const artifact = { ...body, assinatura: hash(JSON.stringify(body)) };
  await writeFile(path.join(root, 'indicadores.json'), JSON.stringify(artifact));
  assert.equal((await readIndicators(root)).indicatorsCurrent, true);
  await writeFile(path.join(root, 'parecer.json'), '{}');
  assert.equal((await readIndicators(root)).indicatorsCurrent, false);
  await rm(path.join(root, 'parecer.json'));
  await writeFile(path.join(root, 'indicadores.json'), JSON.stringify({ ...artifact, versao: 2 }));
  assert.equal((await readIndicators(root)).indicatorsCurrent, false);
});
