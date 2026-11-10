import { spawn } from 'node:child_process';
import { resolvePython } from './jobs.js';

export function createRagService({ projectRoot, jobs, getPython = resolvePython, spawnProcess = spawn }) {
  async function middleware(req, res, next) {
    const url = new URL(req.url, 'http://localhost');
    const match = url.pathname.match(/^\/api\/runs\/([A-Za-z0-9_][\w-]{0,99})\/rag\/(status|search)$/);
    if (!match) return next();
    const reply = (code, value) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json; charset=utf-8'); res.setHeader('Cache-Control', 'no-store'); res.end(JSON.stringify(value)); };
    if (!jobs.allowedRequest(req)) return reply(403, { error: 'Consulta disponível apenas no painel local.' });
    if (req.method !== 'GET') return reply(405, { error: 'Método não permitido.' });
    const [, run, action] = match;
    const line = url.searchParams.get('linha');
    const query = url.searchParams.get('consulta');
    if (action === 'search' && (!/^\d{1,7}$/.test(line || '') || Number(line) < 1 || !query?.trim() || query.length > 2000)) return reply(400, { error: 'Informe linha e consulta de até 2000 caracteres.' });
    try {
      const python = await getPython(projectRoot);
      const bootstrap = "import site,runpy; from pathlib import Path; site.addsitedir(str(Path.cwd()/'.venv'/('Lib/site-packages' if __import__('os').name=='nt' else 'lib/python3.13/site-packages'))); runpy.run_module('src.rag',run_name='__main__')";
      const args = ['-c', bootstrap, action, '--execucao', run];
      if (action === 'search') args.push('--linha', line, '--consulta', query);
      const result = await new Promise((resolve, reject) => {
        const child = spawnProcess(python, args, { cwd: projectRoot, windowsHide: true, shell: false, env: { ...process.env, PYTHONUTF8: '1' }, stdio: ['ignore', 'pipe', 'pipe'] });
        let out = '', failed = false;
        child.stdout.setEncoding('utf8');
        const timer = setTimeout(() => { child.kill(); reject(new Error('Consulta excedeu 30 segundos.')); }, 30000);
        child.stdout.on('data', chunk => { out += chunk.toString('utf8'); if (out.length > 100000) { failed = true; child.kill(); } });
        child.stderr.on('data', () => {});
        child.once('error', e => { clearTimeout(timer); reject(e); });
        child.once('close', code => { clearTimeout(timer); if (code || failed) reject(new Error('RAG indisponível: prepare o índice e confira os documentos desta execução.')); else { try { resolve(JSON.parse(out)); } catch { reject(new Error('Resposta RAG inválida.')); } } });
      });
      return reply(200, result);
    } catch (e) { return reply(409, { error: e.message }); }
  }
  return { middleware };
}
