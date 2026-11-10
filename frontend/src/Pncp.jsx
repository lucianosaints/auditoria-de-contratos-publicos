import { ExternalLink, Landmark } from 'lucide-react';
import { pncpEntries, pncpLabels, pncpUrl } from './pncp.js';

const publicDate = value => String(value || '').replace(/^(\d{4})(\d{2})(\d{2})$/, '$3/$2/$1');
const display = value => value == null ? 'não informado' : String(value).replace(/^\((\d+), (\d{4})\)$/, '$1/$2');

export function PncpOverview({ data }) {
  if (!data.pncp) return null;
  const entries = pncpEntries(data);
  const confirmed = entries.filter(e => e.situacao === 'confirmado_por_regras').length;
  return <section className="agent-overview" aria-label="Reconciliação PNCP"><Landmark size={24} /><div><strong>Contratos e documentos no PNCP</strong>
    <p>{confirmed} vínculos confirmados por regras · {entries.length - confirmed} para conferência ou sem correspondência neste recorte.</p>
    <p>{data.pncp.catalogo?.completo ? 'Paginação do recorte concluída.' : 'Consulta parcial ou em andamento; ausência de resultado não é conclusiva.'}</p>
    {data.pncp.catalogo?.erro && <p className="document-warning">{data.pncp.catalogo.erro}</p>}
    {entries.length !== data.pncp.consultas?.length && <p>Há resultados incompatíveis com a coleta ou os alertas atuais. Consulte o PNCP novamente.</p>}
    <small>Use Consultar PNCP → Planejar documentos → Ler documentos → Preparar RAG. A análise com IA é uma ação separada.</small>
  </div></section>;
}

export function PncpDetails({ data, line }) {
  const entry = pncpEntries(data).find(e => e.linha === line);
  if (!entry) return null;
  return <section className="document-dossier" aria-label="Fontes PNCP"><div className="simple-summary-label"><Landmark size={18} />RECONCILIAÇÃO COM O PNCP</div>
    <h3>{pncpLabels[entry.situacao]}</h3><p className="muted">Consulta em {new Date(data.pncp.consultado_em).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}. Publicações de {publicDate(data.pncp.recorte?.data_inicial)} a {publicDate(data.pncp.recorte?.data_final)}.</p>
    {entry.situacao === 'conflitante' && <p className="document-warning">Os candidatos podem ser contratos diferentes, apesar de compartilharem número ou processo. As diferenças não constituem, por si, inconsistência do mesmo contrato ou irregularidade.</p>}
    <p className="simple-note">{data.pncp.limite}</p>
    {entry.candidatos.map((match, i) => <article className="document-item" key={`${match.numero_controle_pncp}-${i}`}>
      <h4>{match.numero_controle_pncp}</h4><p>{match.fornecedor}</p><p>{match.objeto}</p>
      <dl className="source-fields">{(match.comparacoes || []).map(c => <div key={c.campo}><dt>{({ numero_ano: 'Número/ano', processo: 'Processo', cnpj_fornecedor: 'CNPJ do fornecedor', valor_inicial: 'Valor inicial', data_assinatura: 'Assinatura' })[c.campo] || c.campo}</dt><dd>Portal: {display(c.portal)} · PNCP: {display(c.pncp)} · {({ igual: 'coincide', divergente: 'diverge', nao_comparavel: 'não comparável' })[c.resultado] || c.resultado}</dd></div>)}</dl>
      {pncpUrl(match.url) && <a href={pncpUrl(match.url)} target="_blank" rel="noreferrer">Conferir contrato no PNCP <ExternalLink size={14} /></a>}
    </article>)}
    <p>{entry.documentos.length} documentos disponíveis para leitura · {entry.documentos_omitidos || 0} omitidos por limite. Lista de links não significa leitura realizada.</p>
    {entry.status_documentos === 'falhou' && <p className="document-warning">A consulta dos anexos falhou: {entry.erro_documentos}</p>}
    <div className="document-links">{entry.documentos.map(doc => pncpUrl(doc.url) && <a key={doc.id} href={pncpUrl(doc.url)} target="_blank" rel="noreferrer">{doc.rotulo} · {doc.tipo_informado_pncp}<ExternalLink size={14} /></a>)}</div>
  </section>;
}
