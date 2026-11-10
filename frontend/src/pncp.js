const ordered = value => JSON.stringify(Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b, 'en'))));
export const pncpLabels = { confirmado_por_regras: 'Vínculo confirmado por regras', candidato: 'Candidato — conferir identidade',
  conflitante: 'Divergências entre as fontes', nao_localizado_no_recorte: 'Não localizado neste recorte', consulta_incompleta: 'Consulta incompleta' };

export function validatePncp(value) {
  if (!value) return;
  const validMatch = m => m && (typeof m.numero_controle_pncp === 'string' || m.numero_controle_pncp == null) &&
    (typeof m.url === 'string' || m.url == null) && (typeof m.objeto === 'string' || m.objeto == null) &&
    (typeof m.fornecedor === 'string' || m.fornecedor == null) && Array.isArray(m.comparacoes) && m.comparacoes.every(c => c &&
      typeof c.campo === 'string' && ['igual', 'divergente', 'nao_comparavel'].includes(c.resultado) &&
      [c.portal, c.pncp].every(v => v == null || typeof v === 'string'));
  if (value.versao !== 1 || typeof value.limite !== 'string' || typeof value.consultado_em !== 'string' ||
      !Array.isArray(value.linhas) || !value.linhas.every(Number.isInteger) || !Array.isArray(value.consultas) ||
      !value.consultas.every(e => e && Number.isInteger(e.linha) && e.linha > 0 && pncpLabels[e.situacao] &&
        e.registro_original && typeof e.registro_original === 'object' && !Array.isArray(e.registro_original) &&
        Array.isArray(e.candidatos) && e.candidatos.every(validMatch) && Array.isArray(e.documentos) &&
        e.documentos.every(d => d && /^[a-f0-9]{64}$/.test(d.id) && typeof d.rotulo === 'string' && typeof d.url === 'string'))) {
    throw new Error('pncp.json não tem a estrutura esperada.');
  }
}

export function pncpEntries(data) {
  const result = data.pncp;
  if (!result || result.versao !== 1 || !Array.isArray(result.consultas)) return [];
  const lines = [...new Set((data.audit?.suspeitos || []).map(f => f.linha))].sort((a, b) => a - b);
  if (JSON.stringify(result.linhas) !== JSON.stringify(lines)) return [];
  return result.consultas.filter(e => e && Number.isInteger(e.linha) && data.records[e.linha - 1] &&
    e.registro_original && ordered(e.registro_original) === ordered(data.records[e.linha - 1]) &&
    pncpLabels[e.situacao] && Array.isArray(e.candidatos) && Array.isArray(e.documentos));
}

export function pncpUrl(raw) {
  try {
    const url = new URL(raw);
    return url.protocol === 'https:' && url.hostname === 'pncp.gov.br' && !url.username && !url.password &&
      (!url.port || url.port === '443') ? url.href : null;
  } catch { return null; }
}
