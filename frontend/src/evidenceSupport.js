const stable = value => JSON.stringify(sort(value));
function sort(value) {
  if (Array.isArray(value)) return value.map(sort);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, sort(value[k])]));
  return value;
}

export function supportFor(data, item) {
  const report = data?.verification;
  if (!report || report.versao !== 1 || report.revisao_atualizado_em !== data.review?.atualizado_em || !Array.isArray(report.itens)) return null;
  const matches = report.itens.filter(i => i?.linha === item.linha);
  const result = matches.length === 1 ? matches[0] : null;
  if (!result || stable(result.revisao_original) !== stable(item) || !Array.isArray(result.avisos) ||
      !['conferir', 'sem_alertas_nas_regras'].includes(result.status) ||
      result.avisos.some(a => !a || typeof a.codigo !== 'string' || typeof a.trecho !== 'string' || typeof a.mensagem !== 'string') ||
      (result.status === 'conferir') !== (result.avisos.length > 0)) return null;
  return result;
}

export function sourceCoverage(item, review) {
  const sources = [...new Map(item.evidencias.map(e => [e.fonte_id, e.fonte])).values()];
  const pages = type => new Set(sources.filter(s => s.tipo === type && s.pagina).map(s => `${s.documento_id || s.url || s.id}:${s.pagina}`)).size;
  const pdfs = sources.filter(s => s.tipo === 'anexo_portal');
  return { portal: sources.filter(s => ['campo_portal', 'registro_portal'].includes(s.tipo)).length,
    diario: sources.filter(s => s.tipo === 'publicacao_candidata').length,
    paginasDiario: pages('publicacao_candidata'), anexos: new Set(pdfs.map(s => s.documento_id || s.url || s.id)).size,
    paginasPdf: pages('anexo_portal'), ocr: pdfs.some(s => s.metodo?.startsWith('ocr')),
    ficha: pdfs.some(s => s.tipo_documento === 'ficha_portal'),
    rag: sources.some(s => s.rag) ? 'Trechos RAG citados' : review?.rag_transporte === 'mcp_stdio' ? 'Consulta MCP realizada; nenhum trecho RAG citado' :
      Object.hasOwn(review || {}, 'rag_transporte') ? 'RAG/MCP não utilizado nesta revisão' : 'Uso de RAG/MCP sem registro nesta revisão' };
}
