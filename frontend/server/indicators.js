import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';

const hash = value => createHash('sha256').update(value).digest('hex');
const ordered = value => Array.isArray(value) ? value.map(ordered) : value && typeof value === 'object' ?
  Object.fromEntries(Object.keys(value).sort().map(k => [k, ordered(value[k])])) : value;

export async function readIndicators(folder) {
  let indicators;
  try { indicators = JSON.parse(await readFile(path.join(folder, 'indicadores.json'), 'utf8')); }
  catch { return { indicators: null, indicatorsCurrent: false }; }
  try {
    const files = ['contratos.json', 'parecer.json', 'documentos.json', 'pncp.json'];
    const current = await Promise.all(files.map(async name => {
      let bytes;
      try { bytes = await readFile(path.join(folder, name)); }
      catch (e) { if (e.code !== 'ENOENT') throw e; }
      return (bytes ? hash(bytes) : null) === indicators.fontes_sha256?.[name];
    }));
    const { assinatura, ...body } = indicators;
    const intact = assinatura === hash(JSON.stringify(ordered(body)));
    return { indicators, indicatorsCurrent: indicators.versao === 1 && intact && current.every(Boolean) };
  } catch { return { indicators: null, indicatorsCurrent: false }; }
}
