const ordered = value => JSON.stringify(Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)));
export function documentEntry(data, line) {
  const entry = data.documents?.consultas?.find(e => e.linha === line);
  return entry && data.records[line - 1] && ordered(entry.registro_original) === ordered(data.records[line - 1]) ? entry : null;
}
export function validateDocuments(value) {
  if (!value) return;
  const validPage = p => p && Number.isInteger(p.pagina) && p.pagina > 0 && typeof p.texto === 'string' && typeof p.metodo === 'string' &&
    Array.isArray(p.tabelas) && p.tabelas.every(t => Array.isArray(t) && t.every(r => Array.isArray(r) && r.every(c => typeof c === 'string')));
  const validDocument = d => d && /^[a-f0-9]{64}$/.test(d.id) && typeof d.rotulo === 'string' && typeof d.url === 'string' &&
    ['lido', 'parcial', 'nao_lido', 'falhou'].includes(d.status) && Array.isArray(d.paginas) && d.paginas.every(validPage);
  const validEntry = e => e && Number.isInteger(e.linha) && e.linha > 0 && e.registro_original && typeof e.registro_original === 'object' &&
    typeof e.assinatura === 'string' && Array.isArray(e.avisos) && Array.isArray(e.documentos) && e.documentos.every(validDocument);
  if (value.versao !== 1 || !['em_andamento', 'interrompida', 'com_pendencias', 'concluida'].includes(value.status) ||
      typeof value.assinatura !== 'string' || typeof value.limite !== 'string' || !Array.isArray(value.consultas) ||
      !value.consultas.every(validEntry)) {
    throw new Error('documentos.json não tem a estrutura esperada.');
  }
}
