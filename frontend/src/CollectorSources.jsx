import { ExternalLink, Globe, LoaderCircle } from 'lucide-react';
import { safeUrl } from './data.js';

const labels = { consultando: 'Consultando agora', resposta_recebida: 'Resposta recebida', falhou: 'Falha na consulta', cache_local: 'Reutilizando cache local' };
export default function CollectorSources({ data, job, connected }) {
  const office = job?.run_id === data.id ? job.office : null;
  const source = office?.source;
  const url = safeUrl(source?.url);
  const history = Array.isArray(office?.sources) ? office.sources.slice(-6) : [];
  const querying = connected && job?.active && source?.status === 'consultando' && office.agent === 0;
  const status = !source ? 'Aguardando coleta' : !connected ? 'Conexão indisponível · última fonte registrada' : !job.active ? 'Ação encerrada · última fonte registrada' : labels[source.status] || 'Última fonte registrada';
  return <section className="collector-sources" aria-label="Fontes consultadas pelo Coletor">
    <div className="collector-source-icon">{querying ? <LoaderCircle size={20} className="spin" /> : <Globe size={20} />}</div>
    <div className="collector-source-body"><div className="collector-source-title"><strong>Coletor · fontes de dados</strong><span role="status">{status}</span></div>
      {url ? <><span className="collector-source-name">{source.name}</span><a className="collector-source-url" href={url} target="_blank" rel="noreferrer">{url}<ExternalLink size={13} /></a></> : <p>O órgão e a URL aparecem aqui quando uma fonte é consultada nesta ação.</p>}
      {history.length > 1 && <ol className="collector-source-history" aria-label="Sequência de fontes desta ação">{history.map((entry, i) => <li key={`${entry.started_at}-${i}`}><span>{i ? '→' : 'FONTES'}</span>{safeUrl(entry.url) ? <a href={safeUrl(entry.url)} target="_blank" rel="noreferrer" title={entry.url}>{entry.name}</a> : <span>{entry.name}</span>}<small>{labels[entry.status] || 'Registrada'}</small></li>)}</ol>}
      {source && <small>Uma resposta recebida não confirma coleta integral. Só aparecem fontes acessadas por esta ação; o cache é identificado separadamente.</small>}
    </div>
  </section>;
}
