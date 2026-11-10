import { createHash, randomUUID } from 'node:crypto';
import { readFile, writeFile, mkdir, open, unlink, realpath, stat } from 'node:fs/promises';
import path from 'node:path';

const readJson = async file => JSON.parse(await readFile(file, 'utf8'));
const stable = value => JSON.stringify(value, Object.keys(value).sort());
const hashRecord = value => createHash('sha256').update(stable(value)).digest('hex');
const statuses = new Set(['em_analise', 'documentos_solicitados', 'conferido_com_ressalvas', 'alerta_nao_sustentado']);
const fail = (message, status = 400) => Object.assign(new Error(message), { status });
const alive = pid => { if (!Number.isInteger(pid) || pid <= 0) return false; try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };

export function createDocumentsService({ reportsRoot, jobs }) {
  async function context(run, line) {
    const folder = path.join(reportsRoot, run);
    const records = await readJson(path.join(folder, 'contratos.json'));
    if (!Number.isSafeInteger(line) || line < 1 || line > records.length) throw fail('Linha fora da coleta.');
    const manifest = await readJson(path.join(folder, 'documentos.json')).catch(() => null);
    const entry = manifest?.consultas?.find(e => e.linha === line);
    const recordHash = hashRecord(records[line - 1]);
    const audit = await readJson(path.join(folder, 'parecer.json')).catch(() => null);
    const reasons = [...new Set((audit?.suspeitos || []).filter(f => f.linha === line).map(f => f.motivo_suspeita))].sort();
    const auditHash = createHash('sha256').update(JSON.stringify(reasons)).digest('hex');
    const compatible = entry?.registro_sha256 === recordHash;
    return { folder, registro_sha256: recordHash, parecer_sha256: auditHash, documentos_assinatura: compatible ? entry.assinatura : null };
  }
  async function history(folder, line) {
    try { return await readJson(path.join(folder, 'revisoes_humanas', `${line}.json`)); }
    catch (e) { if (e.code === 'ENOENT') return []; throw e; }
  }
  async function middleware(req, res, next) {
    const url = new URL(req.url, 'http://localhost');
    const match = url.pathname.match(/^\/api\/runs\/([A-Za-z0-9_][\w-]{0,99})\/(documentos\/([a-f0-9]{64})|revisoes\/(\d+))$/);
    if (!match) return next();
    const reply = (code, value) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json; charset=utf-8'); res.end(JSON.stringify(value)); };
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    if (!jobs.allowedRequest(req)) return reply(403, { error: 'Acesso disponível apenas no painel local.' });
    try {
      const [, run, , documentId, lineValue] = match;
      if (documentId) {
        if (req.method !== 'GET') return reply(405, { error: 'Método não permitido.' });
        const folder = path.join(reportsRoot, run);
        const manifest = await readJson(path.join(folder, 'documentos.json'));
        const document = manifest.consultas.flatMap(e => e.documentos).find(d => d.id === documentId && d.arquivo);
        if (!document) throw fail('Documento não disponível.', 404);
        const directory = await realpath(path.join(folder, 'documentos'));
        const filename = await realpath(path.join(directory, `${documentId}.pdf`));
        if (path.dirname(filename) !== directory) throw fail('Caminho não permitido.', 403);
        const bytes = await readFile(filename);
        if (createHash('sha256').update(bytes).digest('hex') !== document.sha256) throw fail('O documento local mudou. Execute Ler documentos novamente.', 409);
        res.setHeader('Content-Type', 'application/pdf');
        res.setHeader('Content-Disposition', `inline; filename="${documentId}.pdf"`);
        res.setHeader('Content-Security-Policy', "sandbox; default-src 'none'");
        return res.end(bytes);
      }
      const line = Number(lineValue);
      const ctx = await context(run, line);
      if (req.method === 'GET') return reply(200, { ...ctx, folder: undefined, historico: await history(ctx.folder, line) });
      if (req.method !== 'POST') return reply(405, { error: 'Método não permitido.' });
      if (!jobs.authorized(req)) throw fail('Atualize o painel antes de salvar.', 403);
      if (Number(req.headers['content-length']) > 18000) throw fail('Registro muito grande.', 413);
      req.setEncoding('utf8');
      let raw = '';
      for await (const chunk of req) { raw += chunk.toString(); if (Buffer.byteLength(raw) > 18000) throw fail('Registro muito grande.', 413); }
      let body;
      try { body = JSON.parse(raw); } catch { throw fail('JSON inválido.'); }
      const allowed = ['situacao', 'responsavel', 'nota', 'registro_sha256', 'documentos_assinatura', 'parecer_sha256', 'anterior'];
      if (!body || Array.isArray(body) || Object.keys(body).some(k => !allowed.includes(k)) ||
          !statuses.has(body.situacao) || typeof body.responsavel !== 'string' || !body.responsavel.trim() || body.responsavel.length > 100 ||
          typeof body.nota !== 'string' || !body.nota.trim() || body.nota.length > 4000) throw fail('Informe responsável, situação e justificativa (até 4000 caracteres).');
      if (body.registro_sha256 !== ctx.registro_sha256 || body.documentos_assinatura !== ctx.documentos_assinatura || body.parecer_sha256 !== ctx.parecer_sha256) throw fail('As fontes mudaram. Reabra o contrato para revisar.', 409);
      const directory = path.join(ctx.folder, 'revisoes_humanas');
      await mkdir(directory, { recursive: true });
      const lock = path.join(directory, `${line}.lock`);
      let handle;
      try { handle = await open(lock, 'wx'); } catch (e) {
        if (e.code !== 'EEXIST') throw e;
        const owner = await readJson(lock).catch(() => null);
        const age = await stat(lock).then(s => Date.now() - s.mtimeMs, () => 0);
        if ((owner && !alive(owner.pid)) || (!owner && age > 30000)) {
          await unlink(lock).catch(() => {});
          try { handle = await open(lock, 'wx'); } catch { throw fail('Outra revisão está sendo salva. Tente novamente.', 409); }
        } else throw fail('Outra revisão está sendo salva. Tente novamente.', 409);
      }
      try {
        await handle.writeFile(JSON.stringify({ pid: process.pid }));
        const previous = await history(ctx.folder, line);
        const latest = await context(run, line);
        if (latest.registro_sha256 !== ctx.registro_sha256 || latest.documentos_assinatura !== ctx.documentos_assinatura || latest.parecer_sha256 !== ctx.parecer_sha256) throw fail('As fontes mudaram. Reabra o contrato para revisar.', 409);
        if ((body.anterior ?? null) !== (previous.at(-1)?.id ?? null)) throw fail('Existe uma revisão mais recente. Reabra o contrato.', 409);
        const event = { id: randomUUID(), linha: line, registrado_em: new Date().toISOString(),
          registro_sha256: ctx.registro_sha256, documentos_assinatura: ctx.documentos_assinatura,
          parecer_sha256: ctx.parecer_sha256,
          situacao: body.situacao, responsavel: body.responsavel.trim(), nota: body.nota.trim() };
        const temp = path.join(directory, `${line}.tmp`);
        await writeFile(temp, JSON.stringify([...previous, event], null, 2), 'utf8');
        const { rename } = await import('node:fs/promises');
        await rename(temp, path.join(directory, `${line}.json`));
        return reply(201, { ...ctx, folder: undefined, historico: [...previous, event] });
      } finally { await handle.close(); await unlink(lock); }
    } catch (e) { return reply(e.status || 500, { error: e.status ? e.message : 'Não foi possível acessar o dossiê ou a revisão.' }); }
  }
  return { middleware };
}
