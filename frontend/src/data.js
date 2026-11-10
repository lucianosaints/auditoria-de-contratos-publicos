import { buildSimpleSummary } from './simpleSummary.js';
import { validateAgentReview } from './agentReview.js';
import { validateDocuments } from './documents.js';
import { validatePncp } from './pncp.js';

export const normalize = (v) => String(v ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
export function field(record, aliases) {
  const key = Object.keys(record).find(k => aliases.includes(normalize(k)));
  return key ? String(record[key] ?? '') : '';
}
export function moneyValue(raw) {
  let value = String(raw ?? '').replace(/R\$|\s/g, '');
  if (value.includes(',')) {
    if (!/^-?(?:\d+|\d{1,3}(?:\.\d{3})+),\d{2}$/.test(value)) return null;
    value = value.replace(/\./g, '').replace(',', '.');
  } else if (!/^-?\d+(?:\.\d{2})?$/.test(value)) return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}
export const brl = (v) => v === null ? 'Não informado' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);
export const safeUrl = (raw) => {
  try { const url = new URL(raw); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
};
export function category(text) {
  const value = normalize(text);
  if (/preco|sobrepreco|custo|orcamento/.test(value)) return 'Preços e custos';
  if (/ata|adesao|licitacao/.test(value)) return 'Atas e contratação';
  if (/quantit|escopo|objeto|entregav/.test(value)) return 'Objeto e quantitativos';
  if (/zero|zerad/.test(value)) return 'Valores zerados';
  return 'Outros indícios';
}
export function validateDataset(data) {
  if (!data || !Array.isArray(data.records) || !data.records.every(r => r && typeof r === 'object' && !Array.isArray(r) && Object.values(r).every(v => typeof v === 'string'))) {
    throw new Error('contratos.json deve conter uma lista de registros com campos textuais.');
  }
  if (data.audit && (!Array.isArray(data.audit.suspeitos) || !Array.isArray(data.audit.linhas_analisadas) || typeof data.audit.relatorio_markdown !== 'string' ||
    !data.audit.suspeitos.every(s => Number.isInteger(s.linha) && typeof s.motivo_suspeita === 'string'))) {
    throw new Error('parecer.json não tem a estrutura esperada.');
  }
  if (data.gazette && (typeof data.gazette.limite !== 'string' || !Number.isInteger(data.gazette.edicoes_lidas) ||
      !Array.isArray(data.gazette.consultas) || !data.gazette.consultas.every(q => q && Number.isInteger(q.linha) &&
      Array.isArray(q.resultados) && q.resultados.every(hit => hit && typeof hit.trecho === 'string' && typeof hit.url_pdf === 'string' &&
      typeof hit.edicao === 'string' && typeof hit.fonte === 'string' && Number.isInteger(hit.pagina) && hit.pagina > 0 &&
      Array.isArray(hit.criterios) && hit.criterios.every(c => typeof c === 'string'))))) {
    throw new Error('diario_oficial.json não tem a estrutura esperada.');
  }
  validateAgentReview(data.review);
  validateDocuments(data.documents);
  validatePncp(data.pncp);
  return data;
}
export function buildRows(data) {
  const findings = new Map();
  for (const item of data.audit?.suspeitos || []) {
    if (!Number.isInteger(item.linha) || item.linha < 1 || item.linha > data.records.length) continue;
    const reasons = findings.get(item.linha) || [];
    if (!reasons.includes(item.motivo_suspeita)) reasons.push(item.motivo_suspeita);
    findings.set(item.linha, reasons);
  }
  return data.records.map((record, i) => {
    const reasons = findings.get(i + 1) || [];
    return { id: i + 1, record, reasons, flagged: reasons.length > 0, summary: buildSimpleSummary(record, reasons),
      process: field(record, ['detalhe - processo', 'numero do processo', 'nr [nr processo]', 'nr processo', 'processo']) || `Linha ${i + 1}`,
      supplier: field(record, ['nome do beneficiario', 'beneficiario', 'fornecedor', 'contratado', 'detalhe - contratado']) || 'Fornecedor não informado',
      object: field(record, ['objeto', 'objeto do contrato', 'detalhe - objeto']) || 'Objeto não informado',
      value: moneyValue(field(record, ['valor do contrato', 'valor contratado', 'valor', 'detalhe - valor global'])),
      category: reasons.length ? category(reasons.join(' ')) : 'Sem alerta',
      url: safeUrl(record['URL do contrato']),
    };
  });
}

export const demo = {
  id: 'demonstracao', demo: true,
  records: [
    { 'Processo': 'DEMO-001/2026', 'Nome do Beneficiário': 'Fornecedor demonstrativo A', 'Objeto': 'Fornecimento e instalação de unidades escolares modulares.', 'Valor do Contrato': 'R$ 8.400.000,00', 'Detalhe - Instrumento': 'Termo de adesão', 'Status dos detalhes': 'Exemplo fictício' },
    { 'Processo': 'DEMO-002/2026', 'Nome do Beneficiário': 'Fornecedor demonstrativo B', 'Objeto': 'Aquisição de materiais de limpeza para unidades administrativas.', 'Valor do Contrato': 'R$ 320.000,00' },
    { 'Processo': 'DEMO-003/2026', 'Nome do Beneficiário': 'Fornecedor demonstrativo C', 'Objeto': 'Serviços de manutenção de equipamentos.', 'Valor do Contrato': 'R$ 0,00' },
    { 'Processo': 'DEMO-004/2026', 'Nome do Beneficiário': 'Fornecedor demonstrativo D', 'Objeto': 'Aquisição de 20 computadores com especificações técnicas e garantia de 36 meses.', 'Valor do Contrato': 'R$ 110.000,00' },
    { 'Processo': 'DEMO-005/2026', 'Nome do Beneficiário': 'Fornecedor demonstrativo E', 'Objeto': 'Serviços de apoio administrativo.', 'Valor do Contrato': 'R$ 186.000,00' },
    { 'Processo': 'DEMO-006/2026', 'Nome do Beneficiário': 'Fornecedor demonstrativo F', 'Objeto': 'Fornecimento de 500 resmas de papel A4.', 'Valor do Contrato': 'R$ 15.000,00' },
  ],
  audit: { linhas_analisadas: [1,2,3,4,5,6], suspeitos: [
    { linha: 1, motivo_suspeita: 'Custos e vantajosidade · O objeto menciona “unidades escolares modulares”, sem quantidades ou área no resumo. Solicitar planilha de custos e estudo comparativo com construção convencional. Sobrepreço não verificável com os dados disponíveis. Exemplo fictício.' },
    { linha: 2, motivo_suspeita: 'Quantitativos · O resumo informa “materiais de limpeza”, sem quantidades e unidades de medida. Solicitar termo de referência. A lacuna no resumo não comprova ausência no processo. Exemplo fictício.' },
    { linha: 3, motivo_suspeita: 'Valor zerado · O campo “Valor do Contrato” informa “R$ 0,00” para serviço de manutenção. Conferir se há gratuidade ou erro cadastral. Exemplo fictício.' },
    { linha: 5, motivo_suspeita: 'Objeto genérico · “Serviços de apoio administrativo” não descreve entregáveis mensuráveis no resumo. Solicitar escopo e critérios de medição. Exemplo fictício.' },
  ], relatorio_markdown: '# Relatório demonstrativo\n\nTodos os registros desta tela são fictícios.\n\n## Escopo\nSeis exemplos ilustram a apresentação de alertas e lacunas documentais.\n\n## Diligências\n- Solicitar planilhas de custos e quantitativos.\n- Consultar estudos de vantajosidade e documentos da contratação.\n- Conferir valores zerados com a fonte.\n\nNenhuma conclusão de fraude ou ilegalidade foi emitida.' },
  receipt: null,
};
