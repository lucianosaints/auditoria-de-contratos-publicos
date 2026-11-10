import { useEffect, useState } from 'react';
import { BookOpen, ExternalLink, FileText, Save } from 'lucide-react';
import { safeUrl } from './data.js';
import { documentEntry } from './documents.js';

const labels = { em_analise: 'Em análise', documentos_solicitados: 'Documentos solicitados',
  conferido_com_ressalvas: 'Conferido com ressalvas', alerta_nao_sustentado: 'Alerta não sustentado pelas fontes conferidas' };

export function DocumentsOverview({ data }) {
  if (!data.documents) return null;
  const compatible = data.documents.consultas.filter(e => documentEntry(data, e.linha));
  const docs = new Map(compatible.flatMap(e => e.documentos).map(d => [d.id, d]));
  return <section className="agent-overview" aria-label="Acompanhamento dos documentos"><BookOpen size={24} /><div><strong>Dossiês documentais</strong><p>{[...docs.values()].filter(d => d.status === 'lido').length} PDFs com extração concluída · {[...docs.values()].filter(d => d.status !== 'lido').length} com pendências · {data.documents.status.replaceAll('_', ' ')}.</p><small>Abra um contrato para conferir páginas, tabelas e registrar sua revisão. Ler documentos não chama IA.</small>{compatible.length !== data.documents.consultas.length && <p>Há dossiês de registros anteriores ocultados. Execute Ler documentos novamente.</p>}</div></section>;
}

export function DocumentDetails({ data, line }) {
  const entry = documentEntry(data, line);
  const local = !data.demo && data.id !== 'importado';
  return <section className="document-dossier" aria-label="Dossiê documental"><div className="simple-summary-label"><BookOpen size={18} />DOCUMENTOS E CONFERÊNCIA</div><h3>Fontes que podem ser conferidas</h3>
    {!entry ? <p className="muted">Sem extração compatível para este contrato. Use Planejar documentos e Ler documentos na central de execução. A etapa consulta os anexos dos contratos com achados.</p> : <>
      <p className="muted">{entry.documentos.length} anexos processados · {entry.links_omitidos} links omitidos por limites.</p>
      {entry.avisos.map((text, i) => <p className="document-warning" key={i}>{text}</p>)}
      {!entry.documentos.length && <p>Nenhum link de anexo disponível no inventário desta coleta. Isso não demonstra ausência de documentos no processo.</p>}
      {entry.documentos.map(doc => <article className="document-item" key={doc.id}><h4><FileText size={17} />{doc.rotulo}</h4><p>{({ lido: 'Extração concluída', parcial: 'Leitura parcial', nao_lido: 'Sem texto legível', falhou: 'Não foi possível ler' })[doc.status]}{doc.total_paginas != null && ` · ${doc.paginas.length}/${doc.total_paginas} páginas`}</p>
        {doc.origem === 'pncp' && <p>Fonte PNCP · {doc.numero_controle_pncp} · tipo informado: {doc.tipo_informado_pncp}. Confira o conteúdo no original.</p>}
        {doc.nota_tipo && <p className="document-warning">{doc.nota_tipo}</p>}
        {doc.erro && <p className="document-warning">{doc.erro}</p>}
        {(doc.avisos || []).map((warning, i) => <p className="document-warning" key={i}>{warning}</p>)}
        <div className="document-links">{safeUrl(doc.url) && <a href={safeUrl(doc.url)} target="_blank" rel="noreferrer">Fonte oficial <ExternalLink size={14} /></a>}{local && doc.arquivo && <a href={`/api/runs/${encodeURIComponent(data.id)}/documentos/${doc.id}`} target="_blank" rel="noreferrer">Abrir PDF preservado <ExternalLink size={14} /></a>}</div>
        {doc.sha256 && <small className="document-hash">SHA-256: {doc.sha256}</small>}
        {doc.paginas.map(page => <details className="document-page" key={page.pagina}><summary>Página {page.pagina} · {page.metodo.startsWith('ocr') ? 'OCR local — conferir imagem' : 'Texto do PDF'}{page.truncado ? ' · conteúdo limitado' : ''}</summary>
          <pre>{page.texto || 'Nenhum texto extraído.'}</pre>{page.aviso && <p className="document-warning">{page.aviso}</p>}
          {page.tabelas.map((table, i) => <div className="document-table" key={i}><strong>Tabela extraída {i + 1} — conferir colunas e números</strong><table><tbody>{table.map((row, j) => <tr key={j}>{row.map((cell, k) => <td key={k}>{cell}</td>)}</tr>)}</tbody></table></div>)}
          {local && doc.arquivo && <a href={`/api/runs/${encodeURIComponent(data.id)}/documentos/${doc.id}#page=${page.pagina}`} target="_blank" rel="noreferrer">Conferir esta página no PDF <ExternalLink size={13} /></a>}
        </details>)}
      </article>)}
      <p className="simple-note">{data.documents.limite} A extração não envia documentos aos agentes. Use Revisar com agentes para uma nova análise com os trechos disponíveis.</p>
    </>}
    {local ? <HumanReview key={`${data.id}-${line}-${entry?.assinatura || ''}-${JSON.stringify(data.records[line - 1])}-${JSON.stringify(data.audit?.suspeitos?.filter(f => f.linha === line))}`} run={data.id} line={line} /> : <p className="muted">O registro de revisão humana está disponível nas execuções locais.</p>}
  </section>;
}

function HumanReview({ run, line }) {
  const [state, setState] = useState(null);
  const [status, setStatus] = useState('em_analise');
  const [name, setName] = useState('');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/runs/${encodeURIComponent(run)}/revisoes/${line}`).then(async r => {
      if (!r.ok) throw new Error('Não foi possível carregar o histórico da revisão.');
      const value = await r.json(); if (!cancelled) setState(value);
    }).catch(e => { if (!cancelled) { setMessage(e.message); setFailed(true); } });
    return () => { cancelled = true; };
  }, [run, line]);
  async function save(event) {
    event.preventDefault(); setSaving(true); setMessage(''); setFailed(false);
    try {
      const controlResponse = await fetch('/api/control');
      if (!controlResponse.ok) throw new Error('Executor local indisponível.');
      const control = await controlResponse.json();
      const response = await fetch(`/api/runs/${encodeURIComponent(run)}/revisoes/${line}`, { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Audit-Control': control.token },
        body: JSON.stringify({ situacao: status, responsavel: name, nota: note, registro_sha256: state.registro_sha256,
          documentos_assinatura: state.documentos_assinatura, parecer_sha256: state.parecer_sha256, anterior: state.historico.at(-1)?.id ?? null }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Falha ao salvar a revisão.');
      setState(result); setNote(''); setMessage('Revisão registrada no histórico local.');
    } catch (e) { setMessage(e.message); setFailed(true); }
    finally { setSaving(false); }
  }
  return <section className="human-review" aria-label="Registro de revisão humana"><h3>Seu registro de revisão</h3><p className="muted">Registre o que você conferiu e os documentos que ainda precisa solicitar. O histórico preserva cada registro e sua versão das fontes. O nome é informado por você, sem autenticação de identidade.</p>
    <form onSubmit={save}><label>Responsável<input aria-label="Responsável pela revisão" value={name} onChange={e => setName(e.target.value)} maxLength={100} required /></label><label>Situação<select aria-label="Situação da revisão" value={status} onChange={e => setStatus(e.target.value)}>{Object.entries(labels).map(([id, text]) => <option key={id} value={id}>{text}</option>)}</select></label><label>Justificativa e próxima diligência<textarea aria-label="Justificativa da revisão" value={note} onChange={e => setNote(e.target.value)} maxLength={4000} rows={4} required /></label><button className="button primary" type="submit" disabled={!state || saving}><Save size={16} />{saving ? 'Salvando...' : 'Salvar revisão humana'}</button></form>
    {message && <p role={failed ? 'alert' : 'status'}>{message}</p>}
    {state && <details className="human-history"><summary>Histórico de revisões ({state.historico.length})</summary>{[...state.historico].reverse().map(item => {
      const stale = item.registro_sha256 !== state.registro_sha256 || item.documentos_assinatura !== state.documentos_assinatura || item.parecer_sha256 !== state.parecer_sha256;
      return <article key={item.id}><strong>{labels[item.situacao]}</strong><p>{item.responsavel} · {new Date(item.registrado_em).toLocaleString('pt-BR')}{stale ? ' · fontes/alertas mudaram desde este registro' : ''}</p><p className="human-note">{item.nota}</p></article>;
    })}</details>}
  </section>;
}
