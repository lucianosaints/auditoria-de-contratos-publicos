import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import { createRagService } from '../server/rag.js';

async function setup(t) {
  const calls = [];
  const service = createRagService({ projectRoot: 'D:/Auditoria_Cidada', getPython: async () => 'python.exe',
    jobs: { allowedRequest: req => !req.headers.origin },
    spawnProcess: (exe, args, options) => {
      calls.push({ exe, args, options });
      const child = new EventEmitter(); child.stdout = new PassThrough(); child.stderr = new PassThrough(); child.kill = () => {};
      setImmediate(() => { child.stdout.end(JSON.stringify({ status: 'pronto', fontes: [{ texto: 'Cláusula de medição — execução.' }] })); child.emit('close', 0); });
      return child;
    } });
  const server = createServer((req, res) => service.middleware(req, res, () => { res.statusCode = 404; res.end(); }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  return { base: `http://127.0.0.1:${server.address().port}/api/runs/selected/rag`, calls };
}

test('RAG exige origem local, método de leitura e consulta/linha limitadas antes de criar processo', async t => {
  const { base, calls } = await setup(t);
  assert.equal((await fetch(base + '/status', { headers: { Origin: 'https://external.example' } })).status, 403);
  assert.equal((await fetch(base + '/status', { method: 'POST' })).status, 405);
  for (const query of ['linha=0&consulta=valor', 'linha=1', 'linha=1&consulta=' + 'a'.repeat(2001)]) {
    assert.equal((await fetch(base + '/search?' + query)).status, 400);
  }
  assert.equal(calls.length, 0);
});

test('busca passa consulta como argumento literal sem shell e preserva acentos na resposta', async t => {
  const { base, calls } = await setup(t);
  const query = 'medição $(comando) `texto` " OR *';
  const response = await fetch(base + '/search?' + new URLSearchParams({ linha: '43', consulta: query }));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).fontes[0].texto, 'Cláusula de medição — execução.');
  assert.equal(calls[0].options.shell, false);
  assert.equal(calls[0].options.windowsHide, true);
  assert.equal(calls[0].args.at(-1), query);
  assert.ok(calls[0].args.includes('selected'));
});
