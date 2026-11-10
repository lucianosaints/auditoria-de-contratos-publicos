import { Landmark, ExternalLink } from 'lucide-react';
import { financialEntries, financialUrl } from './financial.js';
import { exactBrl } from './indicators.js';

const number = v => Array.isArray(v) ? v.join('/') : 'não identificado';
const sourceDate = value => {
  const parsed = typeof value === 'string' ? new Date(value) : null;
  return parsed && Number.isFinite(parsed.getTime()) ? parsed.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' }) : 'data não informada';
};
const display = v => v == null ? 'não informado' : Array.isArray(v) ?
  (Array.isArray(v[0]) ? v.map(number).join(', ') || 'não informado' : number(v)) : String(v);
const labels = { consultada: 'Consulta filtrada conferida', consulta_falhou: 'Consulta indisponível',
  limite_fornecedores: 'Consulta omitida pelo limite', identificacao_insuficiente: 'CNPJ ou exercício insuficiente' };

export function FinancialOverview({ data, onOpenLine }) {
  if (!data.financial) return null;
  const entries = financialEntries(data);
  if (!entries) return <section className="agent-overview" aria-label="Consulta financeira"><Landmark size={24} /><div><strong>Consulta financeira desatualizada ou incompatível</strong><p>Consulte novamente para conferir as fontes atuais.</p></div></section>;
  const conflicts = entries.filter(e => e.vinculos.some(v => v.situacao === 'conflito_identidade'));
  const failures = data.financial.consultas_fornecedores.filter(q => q.situacao === 'consulta_falhou').length;
  return <section className="agent-overview" aria-label="Consulta financeira"><Landmark size={24} /><div><strong>Empenhos e movimentações publicados</strong>
    <p>{data.financial.processados}/{data.financial.linhas.length} contratos processados · {data.financial.detalhes_consultados} detalhes consultados · {conflicts.length} contratos com conflito de identidade.</p>
    <p>{failures} consultas de fornecedor indisponíveis · {entries.filter(e => e.situacao_consulta === 'limite_fornecedores').length} contratos fora do limite de consultas · {entries.reduce((n, e) => n + (e.omitidos_por_limite || 0), 0)} relações omitidas pelo limite de detalhes.</p>
    <p>{data.financial.limite}</p><small>Até {data.financial.configuracao.max_suppliers} consultas por CNPJ/exercício e {data.financial.configuracao.max_details} detalhes por ação. Fontes compatíveis são reutilizadas por até {data.financial.configuracao.cache_hours} horas. Execução dos contratos ainda não avaliável.</small>
    {Array.isArray(data.financial.reverificacoes) && data.financial.reverificacoes.length > 0 && <p>Houve reconsulta pontual de detalhes. As demais relações mantêm suas datas e cobertura originais; confira a data em cada vínculo.</p>}
    {conflicts.length > 0 && <details className="financial-conflicts"><summary>Ver contratos com conflito ({conflicts.length})</summary><div className="support-links">{conflicts.map(e => <button className="button outline small" key={e.linha} onClick={() => onOpenLine(e.linha)}>Conferir conflito da linha {e.linha}</button>)}</div></details>}
    {entries.filter(e => e.vinculos.some(v => v.situacao === 'vinculo_pendente')).map(e => <button className="text-button" key={e.linha} onClick={() => onOpenLine(e.linha)}>Conferir vínculo pendente da linha {e.linha}</button>)}
  </div></section>;
}

export function FinancialDetails({ data, line }) {
  const entry = financialEntries(data)?.find(e => e.linha === line);
  if (!entry) return null;
  return <section className="document-dossier" aria-label="Empenhos do contrato"><div className="simple-summary-label"><Landmark size={18} />CONSULTA FINANCEIRA</div>
    <h3>Vínculos e identidades para conferência</h3><p>{labels[entry.situacao_consulta] || 'Consulta em andamento'}.</p>
    {entry.erro_fonte && <p className="document-warning">Fonte local incompatível: {entry.erro_fonte}</p>}
    {!entry.vinculos.length && <p>Nenhum detalhe consultado para esta linha. Isso não comprova ausência de despesa.</p>}
    {entry.omitidos_por_limite > 0 && <p>{entry.omitidos_por_limite} relações não lidas pelo limite de detalhes.</p>}
    {entry.vinculos.map((v, i) => <article className="document-item" key={i}>
      <h4>Empenho esperado: {number(v.numero_ano_esperado)}</h4>
      <p>{v.origem === 'link_publicado_no_contrato' ? 'Link publicado no contrato' : 'Candidato por CNPJ e processo'}</p>
      {v.numero_ano_observado && <p>Número no detalhe: {number(v.numero_ano_observado)}</p>}
      <p>Fonte consultada em {sourceDate(v.consultado_em)} (horário de Brasília).</p>
      <p className={v.situacao === 'conflito_identidade' ? 'document-warning' : ''}>{v.motivo}</p>
      {v.comparacoes?.length > 0 && <dl className="source-fields">{v.comparacoes.map(c => <div key={c.campo}><dt>{({processo_resumo: 'Processo no resumo do empenho', contrato_resumo: 'Contrato citado no resumo', cnpj_consulta: 'CNPJ na consulta filtrada', processo_consulta: 'Processo na consulta filtrada'})[c.campo] || c.campo}</dt><dd>Contrato: {display(c.contrato)} · Empenho: {display(c.empenho)} · {({igual: 'coincide', divergente: 'diverge', ambiguo: 'múltiplas referências', nao_comparavel: 'não comparável'})[c.resultado]}{c.referencias_invalidas?.length > 0 && ` · Referências com formato inválido: ${c.referencias_invalidas.join(', ')}`}</dd></div>)}</dl>}
      {v.situacao === 'vinculo_pendente' && v.detalhe && <><p><strong>Saldos publicados deste empenho; vínculo contratual pendente.</strong></p>
        <dl className="source-fields">{Object.entries(v.detalhe.saldos_publicados).map(([k, value]) => <div key={k}><dt>{k}</dt><dd>{exactBrl(value)}</dd></div>)}</dl>
        <details><summary>Movimentações publicadas ({v.detalhe.movimentacoes.length})</summary><p>Eventos preservados como publicados, sem soma ou reconciliação de estornos.</p>{v.detalhe.movimentacoes.map((m, n) => <p key={n}>{m.Data} · {m.Tipo} · {m.Valor} · {m.Histórico}</p>)}</details></>}
      {financialUrl(v.url) && <a href={financialUrl(v.url)} target="_blank" rel="noreferrer">Conferir fonte do empenho <ExternalLink size={14} /></a>}
    </article>)}
    <p className="simple-note">{data.financial.limite}</p>
  </section>;
}
