import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, BadgeCheck, BookOpen, Building2, ChartNoAxesCombined, Check, ChevronDown, ChevronLeft, ChevronRight, CircleAlert, ClipboardCheck, Database, ExternalLink, FileCheck2, FileSearch, FileText, FolderOpen, Landmark, LayoutDashboard, ListFilter, LoaderCircle, Menu, RefreshCw, Search, ShieldCheck, Sparkles, Upload, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { brl, buildRows, demo, safeUrl, validateDataset } from './data.js';
import { reviewState } from './agentReview.js';
import { AgentReviewDetails, AgentReviewOverview } from './AgentReview.jsx';
import RunControls from './RunControls.jsx';
import { DocumentDetails } from './Documents.jsx';
import { PncpDetails } from './Pncp.jsx';
import { IndicatorsOverview, IndicatorDetails } from './Indicators.jsx';
import { FinancialDetails } from './Financial.jsx';
import EvidenceWorkspace from './EvidenceWorkspace.jsx';
import Overview from './Overview.jsx';

const defaultPortal = 'https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao';
const nav = [
  { id: 'overview', label: 'Visão geral', title: 'Visão geral da auditoria', description: 'O essencial da execução selecionada e os próximos pontos de atenção.', icon: LayoutDashboard },
  { id: 'contracts', label: 'Contratos', title: 'Contratos sob análise', description: 'Encontre um registro e confira suas fontes e os fundamentos dos alertas.', icon: FileSearch },
  { id: 'evidence', label: 'Evidências', title: 'Fontes e evidências', description: 'Documentos, PNCP e dados financeiros, organizados por fonte.', icon: FolderOpen },
  { id: 'indicators', label: 'Indicadores', title: 'Indicadores da coleta', description: 'Cobertura, exclusões e distribuição dos valores contratuais.', icon: ChartNoAxesCombined },
  { id: 'report', label: 'Relatório', title: 'Relatório de auditoria', description: 'Leia o parecer da execução e consulte seu registro de arquivamento.', icon: FileText },
  { id: 'operations', label: 'Operações', title: 'Operações da auditoria', description: 'Execute uma etapa, consulte seu andamento e acompanhe o resultado.', icon: Activity },
  { id: 'method', label: 'Como analisamos', title: 'Como analisamos', description: 'Conheça o alcance e os limites da triagem automatizada.', icon: BookOpen },
];
function download(name, text, type = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Empty({ title, children }) {
  return <div className="empty"><FolderOpen size={34} /><h3>{title}</h3><p>{children}</p></div>;
}

function SimpleSummary({ summary }) {
  if (!summary) return null;
  return <section className="simple-summary" aria-label="Resumo em linguagem simples"><div className="simple-summary-label"><BookOpen size={17} />ENTENDA EM LINGUAGEM SIMPLES</div><h3>{summary.titulo}</h3><p className="simple-intro">{summary.em_resumo}</p><div className="simple-points"><p><strong>O problema principal</strong>{summary.problema_principal}</p><p><strong>O que isso significa na prática</strong>{summary.significado_pratico}</p><p><strong>Próxima diligência sugerida</strong>{summary.proxima_diligencia}</p></div><p className="simple-note">{summary.nota}</p></section>;
}

function GazetteEvidence({ result, line, flagged }) {
  if (!flagged) return null;
  const entry = result?.consultas?.find(item => item.linha === line);
  const hits = Array.isArray(entry?.resultados) ? entry.resultados : [];
  const unavailable = result?.status === 'consulta_indisponivel';
  return <section className="gazette-section" aria-label="Consulta ao Diário Oficial"><div className="simple-summary-label"><Landmark size={18} />PUBLICAÇÕES OFICIAIS</div><h3>O que consta no Diário Oficial</h3>{!result ? <p className="muted">A consulta ao DOM/JOM ainda não foi realizada nesta execução. Use Consultar Diário na central de execução para pesquisar os contratos com achados.</p> : <><p className="gazette-coverage">{result.edicoes_lidas ?? 0} edições lidas · {result.status === 'consulta_parcial' ? 'cobertura parcial' : unavailable ? 'consulta indisponível' : 'consulte os limites da busca'}</p>{unavailable ? <p className="muted">Não foi possível concluir a consulta. Isso não informa se houve ou não publicação.</p> : !hits.length ? <p className="muted">{entry?.status === 'identificacao_insuficiente' ? 'O registro não tem número e ano suficientes para pesquisar com segurança.' : 'Nenhuma referência localizada nas edições consultadas. Isso não comprova ausência de publicação.'}</p> : <><p className="muted">Referências candidatas: confira órgão, fornecedor, objeto e período no documento original.</p>{hits.map((hit, i) => { const pdf = safeUrl(hit.url_pdf); const page = Number.isInteger(hit.pagina) && hit.pagina > 0 ? hit.pagina : null; return <article className="gazette-hit" key={i}><div><strong>{hit.edicao} · {hit.fonte?.toUpperCase()}</strong><span>{page ? `Página ${page}` : 'Página não identificada'}</span></div><blockquote>{hit.trecho}</blockquote><small>Critérios: {(hit.criterios || []).join(', ').replaceAll('_', ' ')}</small>{pdf && <a href={pdf + (page ? `#page=${page}` : '')} target="_blank" rel="noreferrer">Abrir PDF da fonte <ExternalLink size={14} /></a>}</article>; })}</>}<p className="simple-note">{result.limite}</p></>}<a className="text-button" href="https://www.marica.rj.gov.br/diario-oficial-de-marica/" target="_blank" rel="noreferrer">Consultar arquivo oficial <ArrowUpRight size={14} /></a></section>;
}

export default function App() {
  const [data, setData] = useState(demo);
  const [runs, setRuns] = useState([]);
  const [portalConfig, setPortalConfig] = useState({
    url: defaultPortal,
    name: 'Maricá - RJ',
    isECidade: true,
    custom: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [view, setView] = useState('overview');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const input = useRef(null);
  const dialog = useRef(null);
  const requestId = useRef(0);
  const followRun = useRef(null);
  const rows = useMemo(() => buildRows(data), [data]);
  const flagged = rows.filter(r => r.flagged);
  const review = useMemo(() => reviewState(data), [data]);
  const analyzed = new Set((data.audit?.linhas_analisadas || []).filter(i => Number.isInteger(i) && i > 0 && i <= rows.length)).size;
  const coverage = rows.length ? Math.round(analyzed / rows.length * 100) : 0;
  const invalidFindings = (data.audit?.suspeitos || []).filter(s => s.linha < 1 || s.linha > rows.length).length;
  const categories = [...new Set(flagged.map(r => r.category))];
  const report = data.audit?.relatorio_markdown || data.report || '';
  const visible = rows.filter(row => (filter !== 'flagged' || row.flagged) && (filter !== 'clear' || !row.flagged) && (categoryFilter === 'all' || row.category === categoryFilter) && `${row.process} ${row.supplier} ${row.object} ${row.reasons.join(' ')}`.toLocaleLowerCase('pt-BR').includes(search.toLocaleLowerCase('pt-BR')));
  const pages = Math.max(1, Math.ceil(visible.length / 8));
  const paginated = visible.slice((page - 1) * 8, page * 8);

  async function loadRun(id) {
    const ticket = ++requestId.current;
    setLoading(true); setError('');
    try {
      const response = await fetch(`/api/runs/${encodeURIComponent(id)}`);
      if (!response.ok) throw new Error('Não foi possível carregar esta execução.');
      const next = validateDataset(await response.json());
      if (ticket === requestId.current) { setData(next); resetFilters(); }
    } catch (e) { if (ticket === requestId.current) setError(e.message); }
    finally { if (ticket === requestId.current) setLoading(false); }
  }
  async function refresh(initial = false) {
    const ticket = ++requestId.current;
    setLoading(true); setError('');
    try {
      const response = await fetch('/api/runs');
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Arquivos locais indisponíveis. Inicie pelo .bat ou importe contratos.json e parecer.json.');
      const list = await response.json();
      if (!Array.isArray(list)) throw new Error('Lista de execuções inválida.');
      if (ticket !== requestId.current) return;
      setRuns(list);
      if (initial && list.length) await loadRun((list.find(r => r.count > 0 && r.hasAudit) || list.find(r => r.count > 0) || list[0]).id);
      else if (!initial && !data.demo && list.some(r => r.id === data.id)) await loadRun(data.id);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  async function updateFromJob(job, initiated = false) {
    if (initiated) {
      followRun.current = job.run_id;
      if (job.action === 'nova_auditoria') {
        setData({ id: job.run_id, records: [], demo: false });
        resetFilters();
      }
    }
    const ticket = requestId.current;
    try {
      const list = await fetch('/api/runs').then(r => r.ok ? r.json() : null);
      if (!Array.isArray(list) || ticket !== requestId.current) return;
      setRuns(list);
      const target = followRun.current || (!data.demo && data.id === job.run_id ? data.id : null);
      if (!target || !list.some(run => run.id === target)) return;
      const next = await fetch(`/api/runs/${encodeURIComponent(target)}`).then(r => r.ok ? r.json() : null);
      if (next && ticket === requestId.current) {
        validateDataset(next);
        setData(next);
        if (target !== data.id) resetFilters();
        else setSelected(current => current ? buildRows(next).find(row => row.id === current.id) || null : null);
      }
      if (!job.active) followRun.current = null;
    } catch { /* O polling tenta novamente; uma gravação em curso não limpa a tela. */ }
  }

  async function loadPortalConfig() {
    try {
      const res = await fetch('/api/portal-config');
      if (res.ok) {
        const cfg = await res.json();
        if (cfg?.url) setPortalConfig(cfg);
      }
    } catch { /* Mantém configuração padrão */ }
  }

  async function savePortalConfig(newUrl) {
    const res = await fetch('/api/portal-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: newUrl })
    });
    const saved = await res.json();
    if (!res.ok) throw new Error(saved.error || 'Não foi possível salvar o portal.');
    setPortalConfig(saved);
    return saved;
  }

  async function resetPortalConfig() {
    const res = await fetch('/api/portal-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reset: true })
    });
    const restored = await res.json();
    if (!res.ok) throw new Error(restored.error || 'Não foi possível restaurar o portal padrão.');
    setPortalConfig(restored);
    return restored;
  }

  useEffect(() => { 
    refresh(true); 
    loadPortalConfig();
  }, []);
  useEffect(() => { setPage(1); }, [search, filter, categoryFilter, data]);
  useEffect(() => { if (selected && dialog.current && !dialog.current.open) dialog.current.showModal(); }, [selected]);
  function resetFilters() { setSearch(''); setFilter('all'); setCategoryFilter('all'); setPage(1); setSelected(null); }
  function navigate(id) { setView(id); setSidebarOpen(false); }
  function showFlagged() { setFilter('flagged'); setCategoryFilter('all'); setView('contracts'); }
  async function importFiles(event) {
    followRun.current = null;
    ++requestId.current; setLoading(false);
    try {
      const files = [...event.target.files];
      const recordsFile = files.find(f => f.name.toLowerCase() === 'contratos.json');
      const auditFile = files.find(f => f.name.toLowerCase() === 'parecer.json');
      const gazetteFile = files.find(f => f.name.toLowerCase() === 'diario_oficial.json');
      const reviewFile = files.find(f => f.name.toLowerCase() === 'revisao_agentes.json');
      const documentsFile = files.find(f => f.name.toLowerCase() === 'documentos.json');
      const verificationFile = files.find(f => f.name.toLowerCase() === 'verificacao_evidencias.json');
      const pncpFile = files.find(f => f.name.toLowerCase() === 'pncp.json');
      if (!recordsFile) throw new Error('Selecione contratos.json e, se disponível, parecer.json juntos.');
      if (files.some(f => f.size > 15 * 1024 * 1024)) throw new Error('Cada arquivo deve ter até 15 MB.');
      const imported = validateDataset({ id: 'importado', records: JSON.parse(await recordsFile.text()), audit: auditFile ? JSON.parse(await auditFile.text()) : null,
        gazette: gazetteFile ? JSON.parse(await gazetteFile.text()) : null,
        documents: documentsFile ? JSON.parse(await documentsFile.text()) : null,
        verification: verificationFile ? JSON.parse(await verificationFile.text()) : null,
        pncp: pncpFile ? JSON.parse(await pncpFile.text()) : null,
        review: reviewFile ? JSON.parse(await reviewFile.text()) : null, receipt: null, demo: false });
      setData(imported); setError(''); resetFilters();
    } catch (e) { setError(e.message); }
    event.target.value = '';
  }
  function exportCsv() {
    const escape = (value) => { let text = String(value ?? ''); if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`; return `"${text.replaceAll('"', '""')}"`; };
    const lines = [['Linha', 'Processo', 'Fornecedor', 'Objeto', 'Valor', 'Status', 'Motivos', 'Fonte'], ...visible.map(r => [r.id, r.process, r.supplier, r.object, brl(r.value), r.flagged ? 'Revisão humana' : 'Sem alerta no parecer', r.reasons.join('\n'), r.url || ''])];
    download(`auditoria-${data.id}.csv`, '\uFEFF' + lines.map(row => row.map(escape).join(';')).join('\r\n'), 'text/csv;charset=utf-8');
  }
  const selectValue = data.demo ? 'demo' : data.id;
  const runLabel = (id) => /^\d{8}T/.test(id) ? `${id.slice(6,8)}/${id.slice(4,6)}/${id.slice(0,4)} · ${id.slice(9,11)}:${id.slice(11,13)} UTC` : id;
  const currentPage = nav.find(item => item.id === view) || nav[0];

  return <div className="app-shell">
    {sidebarOpen && <button className="sidebar-backdrop" aria-label="Fechar menu" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar ${sidebarOpen ? 'is-open' : ''}`}>
      <a className="brand" href="#" onClick={e => { e.preventDefault(); navigate('overview'); }}><span className="brand-symbol"><ShieldCheck size={28} strokeWidth={1.8} /></span><span>auditoria<span className="brand-second">cidadã<span className="brand-dot">.</span></span></span></a>
      <div className="workspace-label"><span className="live-dot" /> OBSERVATÓRIO DE {portalConfig.name.toUpperCase()}</div>
      <p className="nav-label">ESPAÇO DE ANÁLISE</p>
      <nav aria-label="Navegação principal">{nav.map(item => <button key={item.id} onClick={() => navigate(item.id)} className={`nav-item ${view === item.id ? 'active' : ''}`} aria-current={view === item.id ? 'page' : undefined}><item.icon size={20} /><span>{item.label}</span>{item.id === 'contracts' && <small>{rows.length}</small>}</button>)}</nav>
      <div className="sidebar-bottom"><span className="avatar">AC</span><div><strong>Controle social</strong><span>Auditoria e acompanhamento local</span></div><BadgeCheck size={18} /></div>
    </aside>

    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" aria-label="Abrir menu" onClick={() => setSidebarOpen(true)}><Menu size={22} /></button><span>Observatório</span><ChevronRight size={14} /><strong>{nav.find(n => n.id === view)?.label}</strong></div><div className="topbar-right"><span className="local-pill"><span />Ambiente local</span><a className="icon-button" href={portalConfig.url} title={`Abrir Portal da Transparência (${portalConfig.name})`} aria-label={`Abrir Portal da Transparência (${portalConfig.name})`} target="_blank" rel="noreferrer"><ExternalLink size={18} /></a></div></header>
      <main>
        <div className="page-heading"><div><div className="eyebrow">OBSERVATÓRIO DE {portalConfig.name.toUpperCase()}</div><h1>{currentPage.title}</h1><p>{currentPage.description}</p></div><button className="button outline import-button" onClick={() => input.current.click()}><Upload size={17} />Importar auditoria</button><input ref={input} type="file" multiple accept=".json,application/json" onChange={importFiles} hidden aria-label="Importar arquivos da auditoria" /></div>

        <div className="dataset-bar"><div className="dataset-source"><Database size={17} /><span>Fonte dos dados</span><div className="select-wrap"><select aria-label="Selecionar execução" value={selectValue} disabled={loading} onChange={e => { followRun.current = null; if (e.target.value === 'demo') { ++requestId.current; setData(demo); resetFilters(); } else loadRun(e.target.value); }}><option value="demo">Demonstração · dados fictícios</option>{!data.demo && data.id !== 'importado' && !runs.some(r => r.id === data.id) && <option value={data.id}>{runLabel(data.id)} · aguardando coleta</option>}{data.id === 'importado' && <option value="importado">Arquivos importados nesta sessão</option>}{runs.map(run => <option value={run.id} key={run.id}>{runLabel(run.id)} · {run.count} registros{run.hasAudit ? '' : ' · sem parecer'}</option>)}</select><ChevronDown size={15} /></div></div><button className="text-button" disabled={loading} onClick={() => refresh()}><RefreshCw size={15} className={loading ? 'spin' : ''} /><span>{loading ? 'Carregando...' : 'Atualizar'}</span></button></div>
        {data.demo && <div className="demo-notice"><Sparkles size={16} /><span><strong>Modo demonstração.</strong> Os contratos e valores exibidos são fictícios. Selecione uma execução ou importe seus arquivos para ver dados reais.</span></div>}
        {data.progress && data.progress.status !== 'concluido' && <div className="demo-notice" role="status"><Activity size={16} /><span><strong>{data.progress.status === 'interrompido' ? 'Análise interrompida.' : data.progress.status === 'revisando_achados' ? 'Agentes investigando e revisando os achados.' : data.progress.status === 'consultando_diario' ? 'Consultando Diário Oficial.' : data.progress.status === 'analise_concluida' ? 'Análise concluída; arquivamento sem confirmação.' : 'Análise em lotes.'}</strong> {data.progress.lotes_concluidos ?? 0} de {data.progress.total_lotes ?? 0} lotes concluídos. Use Atualizar para consultar o progresso salvo.</span></div>}
        {error && <div className="error-notice" role="alert"><CircleAlert size={18} /><span>{error}</span><button className="icon-button" aria-label="Fechar aviso" onClick={() => setError('')}><X size={16} /></button></div>}
        {invalidFindings > 0 && <div className="error-notice" role="status"><CircleAlert size={18} /><span>{invalidFindings} achado(s) com linha fora da coleta não foram associados a contratos.</span></div>}

        <RunControls data={data} loading={loading} onJobUpdate={updateFromJob} mode={view === 'operations' ? 'full' : view === 'overview' ? 'overview' : 'compact'} onOpen={() => navigate('operations')} />
        {view === 'evidence' && <EvidenceWorkspace data={data} onOpenLine={line => setSelected(rows.find(row => row.id === line) || null)} onOperations={() => navigate('operations')} />}
        {view === 'indicators' && <><IndicatorsOverview data={data} onOpenLine={line => setSelected(rows.find(row => row.id === line) || null)} />{!data.indicators && <Empty title="Indicadores ainda não gerados">Use Gerar indicadores em Operações → Análise e revisão para calcular os dados desta execução.</Empty>}</>}
        {view === 'contracts' && !data.demo && data.audit && <details className="workspace-disclosure"><summary>Revisão dos agentes e avisos de suporte</summary><AgentReviewOverview state={review} total={flagged.length} review={data.review} data={data} onOpen={line => setSelected(rows.find(row => row.id === line) || null)} /></details>}

        {view === 'overview' && (
          <Overview 
            rows={rows} 
            flagged={flagged} 
            review={review} 
            coverage={coverage} 
            onFlagged={() => { if (flagged.length) showFlagged(); else navigate('contracts'); }} 
            onNavigate={navigate}
            portalConfig={portalConfig}
            onSavePortalConfig={savePortalConfig}
            onResetPortalConfig={resetPortalConfig}
          />
        )}

        {view === 'contracts' && <section className="contracts-section"><div className="section-heading"><div><h2>{view === 'overview' ? 'Contratos em perspectiva' : 'Explore os registros'} <span className="count-badge">{rows.length}</span></h2><p>Clique em um registro para consultar os dados e as evidências.</p></div><button className="button outline small" disabled={!visible.length} onClick={exportCsv}><ArrowDownToLine size={16} />Exportar seleção</button></div><div className="table-card"><div className="table-controls"><div className="table-tabs" role="group" aria-label="Filtrar alertas">{[['all', 'Todos', rows.length], ['flagged', 'Com indícios', flagged.length], ['clear', 'Sem alerta', rows.length - flagged.length]].map(([id, label, count]) => <button key={id} className={filter === id ? 'selected' : ''} aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}<span>{count}</span></button>)}</div><div className="table-search"><Search size={16} /><input aria-label="Buscar contrato, objeto ou fornecedor" placeholder="Buscar contrato ou fornecedor..." value={search} onChange={e => setSearch(e.target.value)} /></div></div>
          {(view === 'contracts' || categoryFilter !== 'all') && <div className="category-control"><ListFilter size={16} /><label htmlFor="category">Categoria</label><select id="category" value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}><option value="all">Todas as categorias</option>{[...new Set([...categories, ...(categoryFilter === 'all' ? [] : [categoryFilter])])].map(cat => <option key={cat}>{cat}</option>)}</select>{categoryFilter !== 'all' && <button className="text-button" onClick={() => setCategoryFilter('all')}>Limpar</button>}</div>}
          {!visible.length ? <Empty title={rows.length ? 'Nenhum registro neste filtro' : 'Esta coleta está vazia'}>{rows.length ? 'Ajuste a busca ou selecione outra categoria.' : 'Selecione outra execução ou importe uma coleta com contratos.'}</Empty> : <div className="table-scroll"><table><thead><tr><th>CONTRATO / PROCESSO</th><th>FORNECEDOR E OBJETO</th><th>VALOR PUBLICADO</th><th>TRIAGEM</th><th><span className="sr-only">Ação</span></th></tr></thead><tbody>{paginated.map(row => <tr key={row.id}><td><button className="process-link" onClick={() => setSelected(row)}><span className="row-icon"><FileText size={17} /></span><span>{row.process}<small>Linha {row.id} da coleta</small></span></button></td><td><strong className="supplier-name">{row.supplier}</strong><span className="object-excerpt">{row.object}</span></td><td className="money-cell">{brl(row.value)}</td><td><span className={`status ${row.flagged ? 'flagged' : 'clear'}`}>{row.flagged ? <CircleAlert size={13} /> : <Check size={13} />}{row.flagged ? 'Revisão humana' : data.audit ? 'Sem alerta' : 'Sem parecer'}</span></td><td><button className="icon-button row-open" onClick={() => setSelected(row)} aria-label={`Ver detalhes de ${row.process}`}><ArrowUpRight size={18} /></button></td></tr>)}</tbody></table></div>}
          <div className="table-footer"><span>{visible.length ? `${(page - 1) * 8 + 1}–${Math.min(page * 8, visible.length)} de ${visible.length} registros` : '0 registros'}{data.demo ? ' · demonstração' : ''}</span><div className="pagination"><button className="icon-button" aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16} /></button><span>{page} / {pages}</span><button className="icon-button" aria-label="Próxima página" disabled={page >= pages} onClick={() => setPage(p => p + 1)}><ChevronRight size={16} /></button></div></div></div></section>}

        {view === 'report' && <section className="report-layout"><article className="report-card"><div className="report-toolbar"><span><FileCheck2 size={19} />Parecer preliminar</span><button className="button outline small" disabled={!report} onClick={() => download(`relatorio-${data.id}.md`, report)}><ArrowDownToLine size={15} />Baixar relatório</button></div>{report ? <div className="markdown"><ReactMarkdown>{report}</ReactMarkdown></div> : <Empty title="Parecer ainda não disponível">Esta execução contém a coleta, mas não possui um relatório legível.</Empty>}</article><aside className="report-summary"><ClipboardCheck size={26} /><h3>Rastreabilidade da execução</h3><dl><dt>Origem</dt><dd>{data.demo ? 'Demonstração fictícia' : data.id === 'importado' ? 'Arquivos importados' : 'Relatórios locais'}</dd><dt>Linhas na coleta</dt><dd>{rows.length}</dd><dt>Cobertura declarada</dt><dd>{coverage}%</dd><dt>Revisão adicional dos agentes</dt><dd>{review.items.length} de {flagged.length} contratos com achados</dd><dt>Recibo de arquivamento</dt><dd>{data.receipt?.ok ? `${data.receipt.inseridos ?? 0} inserções confirmadas no recibo` : 'Sem confirmação disponível'}</dd></dl><p>A cobertura valida a declaração de análise, sem comprovar a qualidade do raciocínio.</p></aside></section>}

        {view === 'method' && <section className="method-layout"><article className="method-intro"><span className="method-symbol"><ShieldCheck size={39} /></span><h2>Tecnologia para fazer<br />perguntas melhores.</h2><p>O sistema organiza informações públicas e aponta situações para conferência humana. Cada alerta precisa ser lido junto de sua fonte e de suas limitações.</p></article><div className="method-steps">{[{ icon: Database, title: '01 · Coletar com origem', text: 'Registros do portal e detalhes dos contratos são preservados em arquivos locais. Links de documentos não significam que os anexos foram lidos.' }, { icon: Search, title: '02 · Analisar com contexto', text: 'O parecer procura valores zerados, lacunas de quantitativos e coincidências. Sobrepreço exige referências documentadas e comparáveis.' }, { icon: ClipboardCheck, title: '03 · Conferir as evidências', text: 'Após a triagem, o investigador organiza citações dos campos e do Diário. O revisor aplica procedimentos por assunto e questiona os alertas. Citações e linha são conferidas em Python; a interpretação requer revisão humana.' }, { icon: Building2, title: '04 · Preservar a conclusão humana', text: 'Indício não comprova fraude ou ilegalidade. Sem alerta não equivale a regularidade. Falhas e limites de paginação podem gerar coletas parciais.' }].map(step => <article key={step.title}><span><step.icon size={22} /></span><div><h3>{step.title}</h3><p>{step.text}</p></div></article>)}</div></section>}

        <div className="responsibility-note"><ShieldCheck size={18} /><p><strong>Indícios orientam a investigação.</strong> A triagem não comprova irregularidades e requer revisão humana. “Sem alerta” não significa regularidade.</p></div>
        <footer className="footer"><span>Auditoria Cidadã <span>·</span> Observatório de contratos públicos</span><a href={portalConfig.url} target="_blank" rel="noreferrer">Portal da Transparência de {portalConfig.name} <ArrowUpRight size={13} /></a></footer>
      </main>
    </div>

    <dialog ref={dialog} className="detail-dialog" onClose={() => setSelected(null)} onClick={e => { if (e.target === dialog.current) dialog.current.close(); }}>{selected && <div className="detail-content"><div className="detail-heading"><span className="section-kicker">EVIDÊNCIAS DO CONTRATO</span><button className="icon-button" aria-label="Fechar detalhes" autoFocus onClick={() => dialog.current.close()}><X size={22} /></button></div><span className={`status ${selected.flagged ? 'flagged' : 'clear'}`}>{selected.flagged ? <CircleAlert size={14} /> : <Check size={14} />}{selected.flagged ? 'Revisão humana' : 'Sem alerta no parecer'}</span><h2>{selected.process}</h2><p className="detail-supplier">{selected.supplier}</p><div className="detail-value"><span>VALOR PUBLICADO</span><strong>{brl(selected.value)}</strong></div><h3>Objeto publicado</h3><p className="detail-object">{selected.object}</p><SimpleSummary summary={selected.summary} /><IndicatorDetails data={data} line={selected.id} /><FinancialDetails data={data} line={selected.id} /><PncpDetails data={data} line={selected.id} /><DocumentDetails data={data} line={selected.id} /><GazetteEvidence result={data.gazette} line={selected.id} flagged={selected.flagged} /><AgentReviewDetails state={review} line={selected.id} flagged={selected.flagged} data={data} />{selected.reasons.length ? <details className="technical-findings"><summary>Ver fundamentação técnica ({selected.reasons.length})</summary>{selected.reasons.map((reason, i) => <div className="reason" key={i}><CircleAlert size={19} /><p>{reason}</p></div>)}</details> : <p className="muted">Não há achados associados a esta linha no parecer disponível. Isso não confirma a regularidade do contrato.</p>}<h3>Dados da fonte</h3><dl className="source-fields">{Object.entries(selected.record).filter(([key]) => !['Objeto', 'Links publicados nos detalhes'].includes(key)).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || 'Não informado'}</dd></div>)}</dl>{(() => { let links = []; try { links = JSON.parse(selected.record['Links publicados nos detalhes'] || '[]'); } catch { /* Campo externo ilegível. */ } return Array.isArray(links) && links.length ? <><h3>Links publicados</h3><p className="muted">A presença do link não confirma a leitura de seu conteúdo.</p><div className="document-links">{links.filter(link => safeUrl(link.url)).map((link, i) => <a key={i} href={safeUrl(link.url)} target="_blank" rel="noreferrer"><FileText size={17} />{link.rotulo || 'Documento publicado'}<ExternalLink size={14} /></a>)}</div></> : null; })()}{selected.url && <a className="button primary source-button" href={selected.url} target="_blank" rel="noreferrer">Consultar contrato no portal <ExternalLink size={16} /></a>}<div className="detail-disclaimer"><ShieldCheck size={17} />Confira o contexto e os documentos antes de concluir.</div></div>}</dialog>
      {loading && <div className="loading-indicator" role="status"><LoaderCircle size={17} className="spin" />Carregando arquivos da execução...</div>}
  </div>;
}
