import { spawn } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { access, mkdir, open, readFile, readdir, stat, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

export const ACTIONS = new Set(['nova_auditoria', 'retomar_auditoria', 'consultar_diario', 'revisar_achados', 'planejar_revisao', 'planejar_documentos', 'coletar_documentos', 'preparar_rag', 'verificar_mcp', 'conferir_suporte', 'consultar_pncp', 'gerar_indicadores', 'consultar_financeiro']);
const validId = value => typeof value === 'string' && /^[A-Za-z0-9_][\w-]{0,99}$/.test(value);
const alive = pid => { if (!Number.isInteger(pid) || pid <= 0) return false; try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };
const exists = file => access(file).then(() => true, () => false);
const readJson = async file => JSON.parse(await readFile(file, 'utf8'));
const fail = (message, status = 400) => Object.assign(new Error(message), { status });
const makeId = () => new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z') + '_' + randomUUID().slice(0, 8);
export function redact(text) {
  return text.replace(/([?&](?:key|api_key|token)=)[^&\s]+/gi, '$1[oculto]').replace(/AIza[\w-]{20,}|sk-[\w-]{16,}/g, '[credencial oculta]');
}

export async function resolvePython(root) {
  const candidates = [path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')];
  if (process.env.LOCALAPPDATA) candidates.push(path.join(process.env.LOCALAPPDATA, 'Programs/Python/Python313/python.exe'));
  if (process.platform === 'win32') candidates.push(path.join(os.homedir(), 'AppData/Local/Programs/Python/Python313/python.exe'));
  for (const executable of new Set(candidates)) {
    if (!await exists(executable)) continue;
    const works = await new Promise(resolve => {
      const child = spawn(executable, ['--version'], { windowsHide: true, shell: false, stdio: 'ignore' });
      const timer = setTimeout(() => { child.kill(); resolve(false); }, 5000);
      child.once('error', () => { clearTimeout(timer); resolve(false); });
      child.once('close', code => { clearTimeout(timer); resolve(code === 0); });
    });
    if (works) return executable;
  }
  throw fail('Python funcional não encontrado. Verifique a instalação e o ambiente do projeto.', 503);
}

export function createJobsService({ projectRoot, getPython = resolvePython, spawnProcess = spawn } = {}) {
  const root = path.resolve(projectRoot);
  const jobsRoot = path.join(root, 'data/ui_jobs');
  const reportsRoot = path.join(root, 'data/reports');
  const token = randomBytes(32).toString('hex');
  const metadata = id => path.join(jobsRoot, `${id}.json`);
  const save = (id, value) => writeFile(metadata(id), JSON.stringify(value, null, 2), 'utf8');

  async function readJob(id, logs = false) {
    if (!validId(id)) throw fail('Ação não encontrada.', 404);
    let job;
    try { job = await readJson(metadata(id)); } catch { throw fail('Ação não encontrada.', 404); }
    if (!ACTIONS.has(job.action) || job.id !== id || !validId(job.run_id)) throw fail('Registro de ação inválido.', 404);
    const pending = ['iniciando', 'em_andamento'].includes(job.status);
    const startup = job.status === 'iniciando' && !job.pid && Date.now() - Date.parse(job.created_at) < 30000;
    const active = pending && (alive(job.pid) || startup);
    if (pending && !active) job = { ...job, status: 'interrompido', mensagem: 'O processo não está mais em execução. Você pode retomar os checkpoints salvos.' };
    if (active && await exists(path.join(jobsRoot, `${id}.cancel`))) job = { ...job, status: 'parando' };
    if (logs) {
      try {
        const handle = await open(path.join(jobsRoot, `${id}.log`), 'r');
        try {
          const { size } = await handle.stat();
          const buffer = Buffer.alloc(Math.min(size, 48000));
          await handle.read(buffer, 0, buffer.length, Math.max(0, size - buffer.length));
          job.log = redact(buffer.toString('utf8')).split(/\r?\n/).slice(-120).join('\n').slice(-48000);
        } finally { await handle.close(); }
      } catch { job.log = ''; }
    }
    return { ...job, active };
  }

  async function list() {
    const files = await readdir(jobsRoot).catch(() => []);
    const jobs = await Promise.all(files.filter(n => /^[\w-]+\.json$/.test(n)).sort().reverse().slice(0, 30)
      .map(n => readJob(n.slice(0, -5)).catch(() => null)));
    return jobs.filter(Boolean);
  }

  async function validateAction(action, runId) {
    if (!ACTIONS.has(action)) throw fail('Ação não permitida.');
    if (action === 'nova_auditoria') {
      if (runId != null) throw fail('Nova auditoria cria uma execução própria.');
      return makeId();
    }
    if (!validId(runId) || !await exists(path.join(reportsRoot, runId, 'contratos.json'))) throw fail('Selecione uma execução local com coleta salva.');
    if (action !== 'retomar_auditoria' && !await exists(path.join(reportsRoot, runId, 'parecer.json'))) throw fail('Esta execução ainda não possui parecer para esta ação.');
    if (action === 'retomar_auditoria') {
      const receipt = await readJson(path.join(reportsRoot, runId, 'arquivamento.json')).catch(() => null);
      const progress = await readJson(path.join(reportsRoot, runId, 'progresso.json')).catch(() => null);
      if (receipt?.ok && progress?.status === 'concluido') throw fail('A auditoria já foi concluída. Use os botões de consulta ou revisão.');
    }
    return runId;
  }

  async function reserve(callback) {
    await mkdir(jobsRoot, { recursive: true });
    const guardPath = path.join(jobsRoot, 'launch.lock');
    let guard;
    try { guard = await open(guardPath, 'wx'); }
    catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const previous = await readJson(guardPath).catch(() => null);
      const age = await stat(guardPath).then(s => Date.now() - s.mtimeMs, () => 0);
      if ((previous && !alive(previous.pid)) || (!previous && age > 10000)) {
        await unlink(guardPath).catch(() => {});
        try { guard = await open(guardPath, 'wx'); } catch { throw fail('Outra ação está sendo iniciada. Aguarde.', 409); }
      } else throw fail('Outra ação está sendo iniciada. Aguarde.', 409);
    }
    try { await guard.writeFile(JSON.stringify({ pid: process.pid })); return await callback(); }
    finally { await guard.close(); await unlink(guardPath).catch(() => {}); }
  }

  async function start(action, runId) {
    return reserve(async () => {
      if ((await list()).some(job => job.active)) throw fail('Já existe uma ação em andamento. Aguarde ou interrompa antes de iniciar outra.', 409);
      const target = await validateAction(action, runId);
      const python = await getPython(root);
      const id = makeId();
      const job = { id, action, run_id: target, status: 'iniciando', created_at: new Date().toISOString(), pid: null };
      await save(id, job);
      const handle = await open(path.join(jobsRoot, `${id}.log`), 'a');
      try {
        const bootstrap = "import site,runpy; site.addsitedir('.venv/Lib/site-packages'); runpy.run_module('src.ui_jobs',run_name='__main__')";
        const child = spawnProcess(python, ['-u', '-c', bootstrap, '--job', id], {
          cwd: root, windowsHide: true, shell: false, detached: true,
          stdio: ['ignore', handle.fd, handle.fd],
          env: { ...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1', OTEL_SDK_DISABLED: 'true' },
        });
        await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
        child.unref();
      } catch (error) {
        await save(id, { ...job, status: 'falhou', mensagem: 'Não foi possível iniciar o Python.', finished_at: new Date().toISOString() });
        throw fail('Não foi possível iniciar o Python. Confira a instalação.', 503);
      } finally { await handle.close(); }
      return readJob(id);
    });
  }

  async function stop(id) {
    const job = await readJob(id);
    if (!job.active) throw fail('Esta ação já foi encerrada.', 409);
    await writeFile(path.join(jobsRoot, `${id}.cancel`), 'interromper\n', 'utf8');
    return readJob(id);
  }

  function allowedRequest(req) {
    try {
      const host = new URL(`http://${req.headers.host}`);
      const remote = req.socket.remoteAddress;
      if (!['127.0.0.1', 'localhost', '[::1]'].includes(host.hostname) ||
          !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(remote)) return false;
      if (req.headers.origin && req.headers.origin !== host.origin) return false;
      return req.headers['sec-fetch-site'] !== 'cross-site';
    } catch { return false; }
  }

  async function middleware(req, res, next) {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname !== '/api/control' && !url.pathname.startsWith('/api/jobs')) return next();
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    const reply = (status, value) => { res.statusCode = status; res.end(JSON.stringify(value)); };
    if (!allowedRequest(req)) return reply(403, { error: 'Controles disponíveis apenas no painel local da mesma origem.' });
    try {
      if (req.method === 'GET' && url.pathname === '/api/control') return reply(200, { token, jobs: await list() });
      const match = url.pathname.match(/^\/api\/jobs\/([\w-]+)$/);
      if (req.method === 'GET' && match) return reply(200, await readJob(match[1], true));
      if (req.method !== 'POST') return reply(405, { error: 'Método não permitido.' });
      if (req.headers['x-audit-control'] !== token || !String(req.headers['content-type']).startsWith('application/json')) return reply(403, { error: 'Atualize o painel antes de executar a ação.' });
      if (Number(req.headers['content-length']) > 2000) return reply(413, { error: 'Pedido muito grande.' });
      let body = '';
      for await (const chunk of req) { body += chunk.toString(); if (Buffer.byteLength(body) > 2000) throw fail('Pedido muito grande.', 413); }
      let parsed;
      try { parsed = JSON.parse(body || '{}'); } catch { throw fail('Pedido JSON inválido.'); }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw fail('Pedido inválido.');
      if (url.pathname === '/api/jobs') {
        if (Object.keys(parsed).some(k => !['action', 'runId'].includes(k))) throw fail('Parâmetro não permitido.');
        return reply(202, await start(parsed.action, parsed.runId));
      }
      const cancel = url.pathname.match(/^\/api\/jobs\/([\w-]+)\/stop$/);
      if (cancel) return reply(200, await stop(cancel[1]));
      return reply(404, { error: 'Ação não encontrada.' });
    } catch (error) { return reply(error.status || 500, { error: error.status ? error.message : 'Falha ao acessar o executor local.' }); }
  }
  return { middleware, start, stop, list, readJob, allowedRequest,
    authorized: req => allowedRequest(req) && req.headers['x-audit-control'] === token && String(req.headers['content-type']).startsWith('application/json') };
}
