import { useEffect, useState } from 'react';

const states = { pronto: 'Índice pronto', nao_preparado: 'Índice ainda não preparado', desatualizado: 'Índice desatualizado — prepare novamente', invalido: 'Índice inválido — prepare novamente' };

export default function RagSearch({ data, job }) {
  const [state, setState] = useState(null);
  const [line, setLine] = useState('1');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setResult(null); setState(null); setError('');
    fetch(`/api/runs/${encodeURIComponent(data.id)}/rag/status`, { signal: controller.signal }).then(async r => {
      const value = await r.json(); if (!r.ok) throw new Error(value.error); return value;
    }).then(setState).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, [data.id, data.documents?.assinatura, job?.finished_at]);
  async function search(event) {
    event.preventDefault(); setBusy(true); setError(''); setResult(null);
    try {
      const response = await fetch(`/api/runs/${encodeURIComponent(data.id)}/rag/search?${new URLSearchParams({ linha: line, consulta: query })}`);
      const value = await response.json(); if (!response.ok) throw new Error(value.error); setResult(value);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <div className="rag-search">
    <h3>Buscar nos documentos</h3>
    <p role="status">{states[state?.status] || 'Verificando índice…'}{state?.trechos != null && ` · ${state.trechos} trechos em ${state.paginas} páginas de ${state.contratos} contratos`}</p>
    <p>Pesquise nos documentos já extraídos da linha informada. Cada resultado mostra a página e o arquivo de origem. Esta busca não usa IA.</p>
    <form onSubmit={search} className="rag-form">
      <label>Linha do contrato<input type="number" min="1" max={data.records.length} required value={line} onChange={e => setLine(e.target.value)} /></label>
      <label>Termos para pesquisar<input required maxLength={2000} value={query} onChange={e => setQuery(e.target.value)} placeholder="Ex.: pagamento medição quantitativos" /></label>
      <button className="button outline" disabled={busy || state?.status !== 'pronto'}>{busy ? 'Buscando…' : 'Buscar evidências'}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {result && <div aria-live="polite"><p>{result.fontes.length} trechos encontrados. {result.limite}</p>{result.fontes.map(source => <article className="rag-hit" key={source.id}>
      <strong>Linha {result.linha} · {source.rotulo} · página {source.pagina}</strong>
      <p>{source.nota_tipo} · {source.metodo} · {source.qualidade}</p>
      <blockquote>{source.texto}</blockquote>
      <a href={`/api/runs/${encodeURIComponent(data.id)}/documentos/${source.documento_id}#page=${source.pagina}`} target="_blank" rel="noreferrer">Conferir PDF original</a>
      <details><summary>Origem e integridade</summary><p>{source.url}</p><p>SHA-256: {source.sha256_pdf}</p><p>Posições {source.inicio}–{source.fim} do texto extraído · {source.id}</p></details>
    </article>)}</div>}
  </div>;
}
