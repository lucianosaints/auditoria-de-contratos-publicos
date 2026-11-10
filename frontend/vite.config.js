import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readdir, readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createJobsService } from './server/jobs.js';
import { createDocumentsService } from './server/documents.js';
import { createRagService } from './server/rag.js';
import { createPortalService } from './server/portal.js';
import { readIndicators } from './server/indicators.js';
import { readFinancial } from './server/financial.js';

const reportsRoot = fileURLToPath(new URL('../data/reports/', import.meta.url));
const readJson = async (file) => JSON.parse(await readFile(file, 'utf8'));

// Relatórios são somente leitura; ações têm rotas próprias no executor local.
function localReports() {
  const projectRoot = fileURLToPath(new URL('..', import.meta.url));
  const jobs = createJobsService({ projectRoot });
  const documents = createDocumentsService({ reportsRoot, jobs });
  const rag = createRagService({ projectRoot, jobs });
  const portal = createPortalService({ projectRoot });
  const middleware = async (req, res, next) => {
    const url = new URL(req.url, 'http://localhost');
    if (!url.pathname.startsWith('/api/')) return next();
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    const reply = (status, value) => { res.statusCode = status; res.end(JSON.stringify(value)); };
    if (req.method !== 'GET') return reply(405, { error: 'Acesso somente para leitura.' });
    try {
      if (url.pathname === '/api/runs') {
        const directories = await readdir(reportsRoot, { withFileTypes: true }).catch(() => []);
        const runs = [];
        for (const dir of directories.filter(d => d.isDirectory() && /^[\w-]+$/.test(d.name))) {
          try {
            const folder = path.join(reportsRoot, dir.name);
            const records = await readJson(path.join(folder, 'contratos.json'));
            if (!Array.isArray(records)) continue;
            const modified = await stat(path.join(folder, 'contratos.json'));
            const hasAudit = await stat(path.join(folder, 'parecer.json')).then(() => true, () => false);
            runs.push({ id: dir.name, count: records.length, updatedAt: modified.mtime.toISOString(), hasAudit });
          } catch { /* Execuções sem coleta legível não são publicadas. */ }
        }
        return reply(200, runs.sort((a,b) => b.id.localeCompare(a.id)));
      }
      const match = url.pathname.match(/^\/api\/runs\/([\w-]+)$/);
      if (!match) return reply(404, { error: 'Execução não encontrada.' });
      const folder = path.join(reportsRoot, match[1]);
      const records = await readJson(path.join(folder, 'contratos.json'));
      const audit = await readJson(path.join(folder, 'parecer.json')).catch(() => null);
      const receipt = await readJson(path.join(folder, 'arquivamento.json')).catch(() => null);
      const progress = await readJson(path.join(folder, 'progresso.json')).catch(() => null);
      const gazette = await readJson(path.join(folder, 'diario_oficial.json')).catch(() => null);
      const review = await readJson(path.join(folder, 'revisao_agentes.json')).catch(() => null);
      const documents = await readJson(path.join(folder, 'documentos.json')).catch(() => null);
      const verification = await readJson(path.join(folder, 'verificacao_evidencias.json')).catch(() => null);
      const pncp = await readJson(path.join(folder, 'pncp.json')).catch(() => null);
      const indicators = await readIndicators(folder);
      const financial = await readFinancial(folder);
      const report = await readFile(path.join(folder, 'relatorio.md'), 'utf8').catch(() => '');
      return reply(200, { id: match[1], records, audit, receipt, report, progress, gazette, review, documents, verification, pncp, ...indicators, ...financial, demo: false });
    } catch { return reply(404, { error: 'Não foi possível ler os arquivos desta execução.' }); }
  };
  return { name: 'local-audit-reports',
    configureServer(server) { server.middlewares.use(portal.middleware); server.middlewares.use(jobs.middleware); server.middlewares.use(documents.middleware); server.middlewares.use(rag.middleware); server.middlewares.use(middleware); },
    configurePreviewServer(server) { server.middlewares.use(portal.middleware); server.middlewares.use(jobs.middleware); server.middlewares.use(documents.middleware); server.middlewares.use(rag.middleware); server.middlewares.use(middleware); }
  };
}

export default defineConfig({
  plugins: [react(), localReports()],
  server: { port: 5173, strictPort: true, fs: { allow: [fileURLToPath(new URL('.', import.meta.url)),
    fileURLToPath(new URL('../src/summary_rules.json', import.meta.url))] } },
  preview: { port: 4173, strictPort: true },
});
