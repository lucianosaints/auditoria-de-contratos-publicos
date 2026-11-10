import { BookOpen, CircleAlert, ExternalLink, FileSearch, ShieldCheck, Workflow } from 'lucide-react';
import { safeUrl } from './data.js';
import { reviewLabels } from './agentReview.js';
import { failureExplanation } from './executionStatus.js';
import EvidenceSupport from './EvidenceSupport.jsx';
import { supportFor } from './evidenceSupport.js';

export function AgentReviewOverview({ state, total, review, data, onOpen }) {
  const checked = state.items.map(i => supportFor(data, i)).filter(Boolean);
  const warnings = checked.filter(i => i.avisos.length).length;
  return <section className="agent-overview" aria-label="Acompanhamento dos agentes">
    <span className="agent-overview-icon"><Workflow size={23} /></span>
    <div><strong>Investigação e revisão dos achados</strong><p>{state.items.length} de {total} contratos com revisão adicional disponível.
      {' '}{state.status === 'em_andamento' ? 'Agentes em andamento; use Atualizar para acompanhar.' : state.status === 'interrompida' ? 'Revisão interrompida. Use Revisar com agentes para retomar.' : state.status === 'nao_realizada' ? 'Use Revisar com agentes para investigar a auditoria salva.' : 'A conclusão continua sujeita à conferência humana.'}
      {state.stale > 0 && ` ${state.stale} revisão(ões) de dados anteriores foram ocultadas. Execute a revisão novamente.`}</p>
      {state.status === 'interrompida' && review?.erro && <p className="execution-failure">{failureExplanation(review.erro)}</p>}
      {review?.modelo && <small>Modelo da revisão: {review.modelo}</small>}</div>
    {review?.incremental && <p className="support-summary">Retomada por contrato: {review.contratos_reaproveitados || 0} reaproveitados · {review.contratos_pendentes || 0} selecionados para nova análise nesta execução.</p>}
    <span className={`agent-counter ${state.status === 'interrompida' || state.stale ? 'warning' : ''}`}>{state.items.length}/{total}</span>
    {data && <div className="support-summary"><p>Suporte conferido por regras: {checked.length}/{state.items.length} · {warnings} contratos com avisos. Confira as fontes e os avisos nos detalhes de cada contrato.</p>
      {onOpen && warnings > 0 && <div className="support-links">{checked.filter(i => i.avisos.length).map(i => <button className="button outline small" key={i.linha} aria-label={`Conferir avisos da linha ${i.linha}`} onClick={() => onOpen(i.linha)}>Linha {i.linha}</button>)}</div>}
    </div>}
  </section>;
}

export function AgentReviewDetails({ state, line, flagged, data }) {
  if (!flagged) return null;
  const item = state.items.find(i => i.linha === line);
  return <section className="agent-review" aria-label="Revisão por agentes especialistas">
    <div className="simple-summary-label"><ShieldCheck size={18} />REVISÃO AUTOMATIZADA ADICIONAL</div>
    <h3>O olhar dos agentes especialistas</h3>
    <div className="agent-stages"><span><FileSearch size={15} />Investigar fontes</span><span><ShieldCheck size={15} />Revisar alertas</span><span><BookOpen size={15} />Explicar</span></div>
    {!item ? <p className="muted">Ainda não há revisão adicional compatível com os dados deste contrato. Use Revisar com agentes na central de execução para executar ou retomar. O alerta original continua disponível na fundamentação técnica.</p> : <>
      <span className={`review-disposition ${item.situacao}`}><CircleAlert size={14} />Classificação da IA: {reviewLabels[item.situacao]}</span>
      {data && <EvidenceSupport data={data} item={item} />}
      <p className="agent-explanation">{item.explicacao_simples}</p>
      <dl className="agent-points"><dt>Até onde podemos concluir</dt><dd>{item.limite}</dd><dt>Próxima diligência sugerida</dt><dd>{item.proxima_diligencia}</dd></dl>
      <details className="agent-evidence"><summary>Conferir citações e procedimentos ({item.evidencias.length})</summary>
        <div className="skill-tags">{item.skills.map(skill => <span key={skill}>{skill.replaceAll('_', ' ')}</span>)}</div>
        {item.evidencias.map((e, index) => { const url = safeUrl(e.fonte.url); return <article key={index} className="agent-citation"><strong>{e.fonte.rotulo}{e.fonte.pagina ? ` · página ${e.fonte.pagina}` : ''}</strong><blockquote>{e.trecho}</blockquote><small>Fonte {e.fonte_id}{e.fonte.tipo === 'publicacao_candidata' ? ' · publicação candidata; conferir associação ao contrato' : ''}{e.fonte.tipo === 'anexo_portal' ? ` · anexo · ${e.fonte.metodo === 'ocr_windows' ? 'OCR: conferir imagem' : 'texto extraído'}` : ''}{e.fonte.truncado ? ' · campo parcialmente disponibilizado' : ''}</small>{url && <a href={e.fonte.pagina ? `${url.split('#')[0]}#page=${e.fonte.pagina}` : url} target="_blank" rel="noreferrer">Abrir fonte da revisão <ExternalLink size={13} /></a>}</article>; })}
      </details>
    </>}
    <p className="agent-note">Revisão feita por IA. A conferência literal das citações não comprova a interpretação. O parecer original foi preservado; diligências são sugestões.</p>
  </section>;
}
