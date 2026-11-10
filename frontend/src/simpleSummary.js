import catalog from '../../src/summary_rules.json' with { type: 'json' };

const normalize = (value) => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();
function field(record, aliases) {
  const key = Object.keys(record).find(key => aliases.includes(normalize(key)));
  return key ? String(record[key] ?? '').trim() : '';
}
function amountOf(raw) {
  let clean = raw.replace(/R\$|\s/g, '');
  if (clean.includes(',')) {
    if (!/^-?(?:\d+|\d{1,3}(?:\.\d{3})+),\d{2}$/.test(clean)) return null;
    clean = clean.replaceAll('.', '').replace(',', '.');
  } else if (!/^-?\d+(?:\.\d{2})?$/.test(clean)) return null;
  const amount = Number(clean);
  return Number.isFinite(amount) ? amount : null;
}

export function buildSimpleSummary(record, reasons) {
  if (!reasons.length) return null;
  const source = normalize(['detalhe - objeto', 'objeto', 'objeto do contrato'].map(key => field(record, [key])).join(' '));
  const reasonText = normalize(reasons.join(' '));
  const amount = amountOf(field(record, ['valor do contrato', 'valor contratado', 'valor']) || field(record, ['detalhe - valor global']));
  const process = field(record, ['detalhe - processo']) || field(record, ['numero do processo', 'nr [nr processo]', 'nr processo', 'processo']);
  const rule = catalog.regras.slice(0, -1).find(candidate => (candidate.id !== 'valor_zero' || amount === 0) && (
    candidate.fonte_contem?.some(marker => source.includes(marker)) || candidate.parecer_contem?.some(marker => reasonText.includes(marker))
  )) || catalog.regras.at(-1);
  const money = amount === null ? null : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(amount).replaceAll('\u00a0', ' ');
  const context = { valor_trecho: money ? ` no valor de ${money}` : '', processo_trecho: process ? ` nº ${process}` : '' };
  const fill = (template) => template.replace(/\{(valor_trecho|processo_trecho)\}/g, (_, key) => context[key]);
  const intro = rule.id === 'sem_cobertura' && ['reconhec', 'divida', 'indeniz'].some(term => source.includes(term)) ? rule.em_resumo_divida : rule.em_resumo;
  return { tipo: rule.id, titulo: rule.titulo, em_resumo: fill(intro), problema_principal: fill(rule.problema_principal),
    significado_pratico: fill(rule.significado_pratico), proxima_diligencia: fill(rule.proxima_diligencia),
    valor_publicado: money, processo: process || null, nota: catalog.nota };
}
