import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { createServer, request } from 'node:http';
import { mkdtemp, mkdir, readFile, writeFile, rm, readdir } from 'node:fs/promises';
import { readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createJobsService, redact } from '../server/jobs.js';

test('consulta financeira usa ação permitida e mantém a execução selecionada', async t => {
  const { service, spawned, root } = await setup(t, { finish: true });
  const job = await service.start('consultar_financeiro', 'selected');
  assert.equal(job.action, 'consultar_financeiro');
  assert.equal(job.run_id, 'selected');
  assert.equal(spawned.length, 1);
  assert.equal(spawned[0].options.cwd, root);
  assert.equal(spawned[0].options.shell, false);
});

async function setup(t, { broken = false, finish = false } = {}) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'audit-ui-jobs-'));
  const jobsRoot = path.join(root, 'data/ui_jobs');
  for (const id of ['selected', 'other']) {
    const folder = path.join(root, 'data/reports', id);
    await mkdir(folder, { recursive: true });
    await writeFile(path.join(folder, 'contratos.json'), '[{}]');
    await writeFile(path.join(folder, 'parecer.json'), '{}');
  }
  const spawned = [];
  const spawnProcess = (exe, args, options) => {
    if (broken) throw new Error('Spawn failed');
    spawned.push({ exe, args, options });
    const child = new EventEmitter(); child.unref = () => {};
    process.nextTick(() => {
      const id = args.at(-1);
      const file = path.join(jobsRoot, `${id}.json`);
      const metadata = JSON.parse(readFileSync(file, 'utf8'));
      writeFileSync(file, JSON.stringify({ ...metadata, pid: process.pid, status: finish ? 'concluido' : 'em_andamento' }));
      writeFileSync(options.stdio[1], 'Log demonstrativo de teste\n');
      child.emit('spawn');
    });
    return child;
  };
  const service = createJobsService({ projectRoot: root, getPython: async () => 'test-python', spawnProcess });
  const server = createServer((req, res) => service.middleware(req, res, () => { res.statusCode = 404; res.end(); }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  t.after(async () => {
    await new Promise(resolve => server.close(resolve));
    assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('audit-ui-jobs-'));
    await rm(root, { recursive: true, force: true });
  });
  const { token } = await fetch(`${base}/api/control`).then(r => r.json());
  const post = (url, body, headers = {}) => fetch(base + url, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Audit-Control': token, ...headers }, body: JSON.stringify(body) });
  return { service, spawned, root, jobsRoot, base, post };
}

test('ação executa apenas módulo permitido, sem shell/janela e na execução selecionada', async t => {
  const { post, spawned, root } = await setup(t);
  const response = await post('/api/jobs', { action: 'revisar_achados', runId: 'selected' });
  assert.equal(response.status, 202);
  const job = await response.json();
  assert.equal(job.run_id, 'selected');
  assert.equal(job.active, true);
  assert.equal(spawned.length, 1);
  assert.equal(spawned[0].options.cwd, root);
  assert.equal(spawned[0].options.shell, false);
  assert.equal(spawned[0].options.windowsHide, true);
  assert.ok(spawned[0].args.includes('--job'));
  assert.ok(spawned[0].args[2].includes('src.ui_jobs'));
});

test('planejamento e coleta documental usam executor e seleção explícita', async t => {
  const { service } = await setup(t, { finish: true });
  for (const action of ['planejar_documentos', 'coletar_documentos', 'conferir_suporte']) {
    const job = await service.start(action, 'selected');
    assert.equal(job.action, action);
    assert.equal(job.run_id, 'selected');
    assert.equal(job.active, false);
  }
});

test('pedidos simultâneos e um segundo servidor não iniciam ações duplicadas', async t => {
  const { post, service, root } = await setup(t);
  const responses = await Promise.all([post('/api/jobs', { action: 'consultar_diario', runId: 'selected' }),
    post('/api/jobs', { action: 'consultar_diario', runId: 'other' })]);
  assert.deepEqual(responses.map(r => r.status).sort(), [202, 409]);
  const restarted = createJobsService({ projectRoot: root, getPython: async () => { throw new Error('Não iniciar'); } });
  assert.ok((await restarted.list()).some(j => j.active));
  await assert.rejects(restarted.start('nova_auditoria'), { status: 409 });
  assert.equal((await service.list()).length, 1);
});

test('nova auditoria recebe ID próprio sem sobrescrever a seleção', async t => {
  const { post } = await setup(t);
  const response = await post('/api/jobs', { action: 'nova_auditoria' });
  assert.equal(response.status, 202);
  const job = await response.json();
  assert.match(job.run_id, /^\d{8}T\d{6}Z_[a-f0-9]{8}$/);
  assert.notEqual(job.id, job.run_id);
});

test('origem externa, token ausente e host não local não disparam execução', async t => {
  const { post, base, spawned } = await setup(t);
  for (const headers of [{ Origin: 'https://example.org' }, { 'X-Audit-Control': 'wrong' }, { 'Sec-Fetch-Site': 'cross-site' }]) {
    assert.equal((await post('/api/jobs', { action: 'nova_auditoria' }, headers)).status, 403, JSON.stringify(headers));
  }
  // fetch substitui Host no Node; request envia o cabeçalho real que queremos testar.
  const hostStatus = await new Promise((resolve, reject) => {
    const req = request(`${base}/api/control`, { headers: { Host: 'example.org' } }, res => { res.resume(); resolve(res.statusCode); });
    req.on('error', reject); req.end();
  });
  assert.equal(hostStatus, 403);
  assert.equal((await fetch(`${base}/api/jobs`, { method: 'POST', body: '{}' })).status, 403);
  assert.equal(spawned.length, 0);
});

test('comandos/caminhos/argumentos arbitrários, importação e execução inexistente são rejeitados', async t => {
  const { post, spawned } = await setup(t);
  for (const body of [
    { action: 'cmd', runId: 'selected' }, { action: 'revisar_achados', runId: '../selected' },
    { action: 'revisar_achados', runId: 'importado' }, { action: 'revisar_achados', runId: 'missing' },
    { action: 'nova_auditoria', command: 'anything' }, { action: 'nova_auditoria', runId: 'selected' },
  ]) assert.equal((await post('/api/jobs', body)).status, 400);
  assert.equal((await post('/api/jobs', { action: 'x'.repeat(3000) })).status, 413);
  assert.equal(spawned.length, 0);
});

test('ações documentais exigem parecer e retomada rejeita execução concluída', async t => {
  const { post, root } = await setup(t);
  await rm(path.join(root, 'data/reports/selected/parecer.json'));
  assert.equal((await post('/api/jobs', { action: 'consultar_diario', runId: 'selected' })).status, 400);
  await writeFile(path.join(root, 'data/reports/selected/arquivamento.json'), '{"ok":true}');
  await writeFile(path.join(root, 'data/reports/selected/progresso.json'), '{"status":"concluido"}');
  assert.equal((await post('/api/jobs', { action: 'retomar_auditoria', runId: 'selected' })).status, 400);
});

test('interrupção sinaliza somente a ação gerenciada e preserva o processo até encerrar', async t => {
  const { post, jobsRoot, service } = await setup(t);
  const job = await post('/api/jobs', { action: 'revisar_achados', runId: 'selected' }).then(r => r.json());
  const stopped = await post(`/api/jobs/${job.id}/stop`, {}).then(r => r.json());
  assert.equal(stopped.status, 'parando');
  assert.equal(stopped.active, true);
  assert.ok((await readdir(jobsRoot)).includes(`${job.id}.cancel`));
  const metadata = JSON.parse(await readFile(path.join(jobsRoot, `${job.id}.json`), 'utf8'));
  await writeFile(path.join(jobsRoot, `${job.id}.json`), JSON.stringify({ ...metadata, status: 'interrompido' }));
  assert.equal((await service.readJob(job.id)).active, false);
  assert.equal((await post(`/api/jobs/${job.id}/stop`, {})).status, 409);
});

test('falha de lançamento não fica marcada como execução ativa', async t => {
  const { post, service } = await setup(t, { broken: true });
  assert.equal((await post('/api/jobs', { action: 'nova_auditoria' })).status, 503);
  const jobs = await service.list();
  assert.equal(jobs[0].status, 'falhou');
  assert.equal(jobs[0].active, false);
});

test('processo encerrado inesperadamente é recuperável e logs são limitados/sem chaves', async t => {
  const { service, jobsRoot } = await setup(t);
  await mkdir(jobsRoot, { recursive: true });
  const id = 'old-job';
  await writeFile(path.join(jobsRoot, `${id}.json`), JSON.stringify({ id, run_id: 'selected', action: 'revisar_achados',
    status: 'em_andamento', pid: 99999999, created_at: new Date(0).toISOString() }));
  await writeFile(path.join(jobsRoot, `${id}.log`), 'x'.repeat(80000) + '\nhttps://example.org/?key=secret\n');
  const job = await service.readJob(id, true);
  assert.equal(job.active, false);
  assert.equal(job.status, 'interrompido');
  assert.ok(job.log.length <= 48000);
  assert.ok(!job.log.includes('key=secret'));
  assert.equal(redact('sk-' + 'a'.repeat(20)), '[credencial oculta]');
});
