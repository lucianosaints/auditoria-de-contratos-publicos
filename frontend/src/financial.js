export function financialEntries(data) {
  const f = data.financial;
  if (!f || f.versao !== 1 || f.politica_identidade !== 2 || !data.financialCurrent || data.demo || data.id === 'importado' ||
      !Array.isArray(f.consultas) || !Array.isArray(f.linhas) || !f.configuracao ||
      !Number.isInteger(f.processados) || !Number.isInteger(f.detalhes_consultados) ||
      !Array.isArray(f.consultas_fornecedores) || typeof f.limite !== 'string') return null;
  const lines = new Set();
  if (!f.consultas.every(e => e && Number.isInteger(e.linha) && e.linha > 0 && e.linha <= data.records.length &&
      !lines.has(e.linha) && lines.add(e.linha) && Array.isArray(e.vinculos) && e.vinculos.every(v =>
        v && ['conflito_identidade', 'vinculo_pendente', 'consulta_falhou'].includes(v.situacao) &&
        Array.isArray(v.numero_ano_esperado) && v.numero_ano_esperado.length === 2 &&
        (v.comparacoes == null || Array.isArray(v.comparacoes) && v.comparacoes.every(c => c &&
          typeof c.campo === 'string' && ['igual', 'divergente', 'ambiguo', 'nao_comparavel'].includes(c.resultado) &&
          (c.referencias_invalidas == null || Array.isArray(c.referencias_invalidas) && c.referencias_invalidas.every(s => typeof s === 'string')))) &&
        typeof v.motivo === 'string' && (v.situacao !== 'vinculo_pendente' ||
          v.detalhe && typeof v.detalhe.saldos_publicados === 'object' && Array.isArray(v.detalhe.movimentacoes))))) return null;
  return f.consultas;
}

export function financialUrl(raw) {
  try {
    const u = new URL(raw);
    return u.protocol === 'https:' && u.host === 'transparencia.marica.rj.gov.br' && !u.username && !u.password && !u.hash &&
      ((/^\/e-cidade\/contratos\/padrao\/\d+\/empenho$/.test(u.pathname) && !u.search) ||
        (/^\/e-cidade\/consulta-empenhos\/\d+\/visualizar$/.test(u.pathname) &&
         ['', '?origin=detailed-encumbrance-search'].includes(u.search))) ? u.href : null;
  } catch { return null; }
}
