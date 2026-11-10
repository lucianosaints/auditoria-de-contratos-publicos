import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';

const hash = value => createHash('sha256').update(value).digest('hex');
const ordered = value => Array.isArray(value) ? value.map(ordered) : value && typeof value === 'object' ?
  Object.fromEntries(Object.keys(value).sort().map(k => [k, ordered(value[k])])) : value;

export async function readFinancial(folder) {
  let financial;
  try { financial = JSON.parse(await readFile(path.join(folder, 'financeiro.json'), 'utf8')); }
  catch { return { financial: null, financialCurrent: false }; }
  try {
    const { assinatura, ...body } = financial;
    let current = financial.versao === 1 && financial.politica_identidade === 2 && assinatura === hash(JSON.stringify(ordered(body))) &&
      financial.coleta_sha256 === hash(await readFile(path.join(folder, 'contratos.json'))) &&
      financial.parecer_sha256 === hash(await readFile(path.join(folder, 'parecer.json')));
    for (const source of financial.fontes_html) {
      const resolved = path.resolve(folder, source.arquivo);
      const relative = path.relative(path.resolve(folder), resolved);
      if (relative.startsWith('..') || path.isAbsolute(relative)) { current = false; break; }
      if (hash(await readFile(resolved)) !== source.sha256) current = false;
    }
    return { financial, financialCurrent: current };
  } catch { return { financial: null, financialCurrent: false }; }
}
