import { documentEntry } from './documents.js';
import { sourceCoverage, supportFor } from './evidenceSupport.js';

const quantity = (value, one, many) => `${value} ${value === 1 ? one : many}`;

export default function EvidenceSupport({ data, item }) {
  const coverage = sourceCoverage(item, data.review);
  const result = supportFor(data, item);
  const entry = documentEntry(data, item.linha);
  const docs = entry?.documentos || [];
  const pending = docs.filter(d => d.status !== 'lido').length;
  return <section className="evidence-support" aria-label="Fontes e suporte da conclusão">
    <h4>Fontes citadas nesta revisão</h4>
    <div className="source-coverage"><span>Portal: <strong>{quantity(coverage.portal, 'campo', 'campos')}</strong></span><span>Diário: <strong>{quantity(coverage.diario, 'fonte', 'fontes')} · {quantity(coverage.paginasDiario, 'página', 'páginas')}</strong></span><span>PDFs: <strong>{quantity(coverage.anexos, 'documento', 'documentos')} · {quantity(coverage.paginasPdf, 'página', 'páginas')}</strong></span></div>
    <p>{coverage.rag}.</p>
    {coverage.ocr && <p>Há citação de OCR: confira números e datas na imagem.</p>}
    {coverage.ficha && <p>Uma fonte é ficha cadastral do portal; isso não representa o instrumento contratual integral.</p>}
    <p>{entry ? `Documentos inventariados agora: ${docs.length}; ${pending} com leitura incompleta ou falha; ${entry.links_omitidos || 0} links omitidos pelos limites.` : 'Nenhum inventário documental compatível disponível para este contrato.'} Disponibilidade não comprova leitura integral pelos agentes.</p>
    <h4>Conferência do suporte</h4>
    {!result ? <p>Conferência ainda não disponível ou desatualizada. Use <strong>Conferir suporte</strong> na central de execução, sem IA.</p> : <>
      <strong className={result.avisos.length ? 'support-warning' : ''}>{result.avisos.length ? 'Conclusão exige conferência humana' : 'Nenhum alerta nas regras verificadas'}</strong>
      {result.avisos.map((warning, i) => <article className="support-alert" key={i}><p>{warning.mensagem}</p><blockquote>{warning.trecho}</blockquote></article>)}
      <p>A triagem usa regras locais e não valida toda a interpretação. Ausência de avisos não confirma a conclusão.</p>
    </>}
  </section>;
}
