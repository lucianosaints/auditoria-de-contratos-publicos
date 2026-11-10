import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { createJobsService } from '../server/jobs.js';
import { createDocumentsService } from '../server/documents.js';
import { documentEntry, validateDocuments } from '../src/documents.js';
import { reviewState } from '../src/agentReview.js';

async function setup(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'audit-documents-'));
  const reports = path.join(root, 'data/reports');
  const folder = path.join(reports, 'selected');
  await mkdir(path.join(folder, 'documentos'), { recursive: true });
  const record = { 'Objeto': 'Documentação para conferência', 'Valor': '10.00' };
  const recordHash = createHash('sha256').update(JSON.stringify(Object.fromEntries(Object.entries(record).sort()))).digest('hex');
  const bytes = Buffer.from('%PDF-1.4\nOriginal de teste');
  const id = 'a'.repeat(64);
  const manifest = { versao: 1, status: 'concluida', assinatura: 'documents-v1', limite: 'Limite documentado', consultas: [
    { linha: 1, registro_original: record, registro_sha256: recordHash, assinatura: 'linha-1', avisos: [], documentos: [
      { id, arquivo: `documentos/${id}.pdf`, status: 'lido', sha256: createHash('sha256').update(bytes).digest('hex'),
        url: 'https://transparencia.marica.rj.gov.br/a.pdf', rotulo: 'Contrato', paginas: [] }] }] };
  await writeFile(path.join(folder, 'contratos.json'), JSON.stringify([record]));
  await writeFile(path.join(folder, 'parecer.json'), JSON.stringify({ suspeitos: [{ linha: 1, motivo_suspeita: 'Conferir' }] }));
  await writeFile(path.join(folder, 'documentos.json'), JSON.stringify(manifest));
  await writeFile(path.join(folder, 'documentos', `${id}.pdf`), bytes);
  const jobs = createJobsService({ projectRoot: root });
  const docs = createDocumentsService({ reportsRoot: reports, jobs });
  const server = createServer((req, res) => jobs.middleware(req, res, () => docs.middleware(req, res, () => { res.statusCode = 404; res.end(); })));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const { token } = await fetch(base + '/api/control').then(r => r.json());
  const endpoint = '/api/runs/selected/revisoes/1';
  const context = await fetch(base + endpoint).then(r => r.json());
  const body = { situacao: 'documentos_solicitados', responsavel: 'Pessoa revisora', nota: 'Conferência: solicitar os atestos.',
    registro_sha256: context.registro_sha256, documentos_assinatura: context.documentos_assinatura,
    parecer_sha256: context.parecer_sha256, anterior: null };
  const post = (payload = body, headers = {}) => fetch(base + endpoint, { method: 'POST', headers: {
    'Content-Type': 'application/json', 'X-Audit-Control': token, ...headers }, body: JSON.stringify(payload) });
  t.after(async () => {
    await new Promise(resolve => server.close(resolve));
    assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('audit-documents-'));
    await rm(root, { recursive: true, force: true });
  });
  return { base, endpoint, folder, id, body, post, manifest, record };
}

test('registro humano preserva histórico, acentos e contexto e rejeita edição concorrente', async t => {
  const { base, endpoint, folder, post, body } = await setup(t);
  const before = await readFile(path.join(folder, 'parecer.json'), 'utf8');
  const first = await post(); assert.equal(first.status, 201);
  const saved = await first.json(); assert.equal(saved.historico[0].nota, body.nota);
  assert.equal((await post()).status, 409);
  const second = await post({ ...body, anterior: saved.historico[0].id, nota: 'Resposta recebida: documento ainda insuficiente.' });
  assert.equal(second.status, 201);
  const state = await fetch(base + endpoint).then(r => r.json());
  assert.equal(state.historico.length, 2);
  assert.equal(await readFile(path.join(folder, 'parecer.json'), 'utf8'), before);
});

test('revisão bloqueia origem/token e payload inválido', async t => {
  const { post, body } = await setup(t);
  for (const headers of [{ Origin: 'https://evil.test' }, { 'X-Audit-Control': '' }]) assert.equal((await post(body, headers)).status, 403);
  for (const payload of [{ ...body, linha: 2 }, { ...body, nota: '' }, { ...body, situacao: 'fraude_comprovada' }, { ...body, responsavel: 'x'.repeat(101) }]) {
    assert.equal((await post(payload)).status, 400);
  }
});

test('trava de revisão interrompida por processo morto é recuperada', async t => {
  const { folder, post } = await setup(t);
  const directory = path.join(folder, 'revisoes_humanas');
  await mkdir(directory);
  await writeFile(path.join(directory, '1.lock'), JSON.stringify({ pid: 2147483647 }));
  assert.equal((await post()).status, 201);
});

test('mudanças no registro, alertas ou documentos exigem nova conferência antes de salvar', async t => {
  const { folder, post, manifest, record } = await setup(t);
  await writeFile(path.join(folder, 'documentos.json'), JSON.stringify({ ...manifest, consultas: [{ ...manifest.consultas[0], assinatura: 'nova' }] }));
  assert.equal((await post()).status, 409);
  await writeFile(path.join(folder, 'documentos.json'), JSON.stringify(manifest));
  await writeFile(path.join(folder, 'parecer.json'), JSON.stringify({ suspeitos: [] }));
  assert.equal((await post()).status, 409);
  await writeFile(path.join(folder, 'contratos.json'), JSON.stringify([{ ...record, Valor: '20.00' }]));
  assert.equal((await post()).status, 409);
});

test('PDF preservado exige ID inventariado, integridade e acesso local', async t => {
  const { base, folder, id } = await setup(t);
  const endpoint = base + '/api/runs/selected/documentos/' + id;
  const good = await fetch(endpoint);
  assert.equal(good.status, 200); assert.equal(good.headers.get('content-type'), 'application/pdf');
  assert.ok(good.headers.get('content-security-policy').includes('sandbox'));
  assert.equal((await fetch(endpoint, { headers: { Origin: 'https://evil.test' } })).status, 403);
  assert.equal((await fetch(base + '/api/runs/selected/documentos/' + 'b'.repeat(64))).status, 404);
  await writeFile(path.join(folder, 'documentos', `${id}.pdf`), 'Modificado');
  assert.equal((await fetch(endpoint)).status, 409);
});

test('importação valida dossiês e oculta fontes de outro registro', async t => {
  const { manifest, record } = await setup(t);
  validateDocuments(manifest);
  assert.ok(documentEntry({ documents: manifest, records: [record] }, 1));
  assert.equal(documentEntry({ documents: manifest, records: [{}] }, 1), null);
  assert.throws(() => validateDocuments({ ...manifest, consultas: [{}] }));
  const data = { records: [record], audit: { suspeitos: [{ linha: 1, motivo_suspeita: 'Conferir' }] }, documents: manifest,
    review: { status: 'concluida', itens: [{ linha: 1, registro_original: record, motivos_originais: ['Conferir'] }] } };
  assert.equal(reviewState(data).items.length, 0);
  data.review.documentos_assinatura = manifest.assinatura;
  assert.equal(reviewState(data).items.length, 1);
});
