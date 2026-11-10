import { useState } from 'react';
import { Activity, ArrowRight, Calculator, ChartNoAxesCombined, Check, CircleAlert, FileSearch, Landmark, LoaderCircle, Pause, Play, RefreshCw, ShieldCheck, Terminal } from 'lucide-react';
import ExecutionStatus from './ExecutionStatus.jsx';
import { actionLabels } from './executionStatus.js';

const groups = [
  { id: 'auditoria', label: 'Auditoria', note: 'Crie uma execução ou continue os lotes salvos. Essas ações usam IA e podem gravar os achados no banco.', actions: [
    ['nova_auditoria', Play, 'Coletar, analisar e arquivar em uma nova execução.'],
    ['retomar_auditoria', RefreshCw, 'Continuar uma auditoria que ainda não foi concluída.'],
  ] },
  { id: 'fontes', label: 'Fontes e documentos', note: 'Consulte fontes públicas e organize os documentos da execução selecionada. Essas ações não usam IA.', actions: [
    ['consultar_pncp', Landmark, 'Relacionar contratos e localizar anexos oficiais.'],
    ['consultar_diario', Landmark, 'Pesquisar publicações no Diário Oficial.'],
    ['consultar_financeiro', Landmark, 'Conferir identidades de empenhos e movimentações.'],
    ['planejar_documentos', Calculator, 'Contar os PDFs candidatos, sem fazer downloads.'],
    ['coletar_documentos', FileSearch, 'Baixar PDFs e extrair texto dos arquivos disponíveis.'],
  ] },
  { id: 'revisao', label: 'Análise e revisão', note: 'Estime a revisão antes de chamar os agentes. Indicadores e conferência de suporte são calculados localmente.', actions: [
    ['gerar_indicadores', ChartNoAxesCombined, 'Calcular cobertura e valores contratuais por fornecedor.'],
    ['planejar_revisao', Calculator, 'Estimar reaproveitamento e chamadas, sem usar IA.'],
    ['revisar_achados', ShieldCheck, 'Investigar e revisar os alertas com IA.'],
    ['conferir_suporte', ShieldCheck, 'Conferir conclusões e citações por regras locais.'],
  ] },
];
const statuses = { iniciando: 'Iniciando', em_andamento: 'Em andamento', parando: 'Interrompendo', concluido: 'Concluído', falhou: 'Não concluído', interrompido: 'Interrompido' };

function JobResult({ job }) {
  const r = job.resultado;
  if (!r) return null;
  return <div className="operation-result">
    {job.action === 'planejar_revisao' && <p>{r.contratos_reaproveitados ?? 0} contratos reaproveitados · {r.contratos_pendentes ?? r.contratos} pendentes · até {r.chamadas_maximas_de_etapas} chamadas de etapas. Estimativa sem IA.</p>}
    {r.edicoes_lidas != null && <p>{r.edicoes_lidas} edições lidas · {r.status_diario?.replaceAll('_', ' ')}.</p>}
    {r.contratos_revisados != null && <p>{r.contratos_revisados} de {r.total_contratos} contratos revisados · {r.contratos_reaproveitados ?? 0} reaproveitados.</p>}
    {r.suporte_verificado != null && <p>{r.suporte_verificado} contratos conferidos · {r.suporte_com_avisos} com avisos para conferência humana.</p>}
    {job.action === 'planejar_documentos' && <p>{r.documentos} PDFs candidatos em {r.contratos} contratos · {r.contratos_sem_links} sem links selecionados · {r.links_omitidos} links omitidos por limites.</p>}
    {r.documentos_processados != null && <p>{r.documentos_processados} documentos processados · {r.status_documentos?.replaceAll('_', ' ')}.</p>}
    {r.rag && <p>Índice preparado: {r.rag.trechos} trechos · {r.rag.paginas} pares contrato/página · {r.rag.contratos} contratos.</p>}
    {r.financeiro && <p>Financeiro: {r.financeiro.contratos} contratos processados · {r.financeiro.detalhes} detalhes consultados · {r.financeiro.conflitos} relações com conflito. Saldos sem atribuição automática ao contrato.</p>}
    {r.pncp && <p>PNCP: {r.pncp.confirmados} vínculos confirmados por regras em {r.pncp.contratos} contratos · {r.pncp.documentos_disponiveis} documentos disponíveis. Use Ler documentos para extrair os PDFs.</p>}
    {r.indicadores && <p>Indicadores: {r.indicadores.linhas_coletadas} linhas · {r.indicadores.linhas_elegiveis_distribuicao} elegíveis · {r.indicadores.linhas_excluidas_distribuicao} excluídas. Consulte a área Indicadores.</p>}
    {r.mcp && <p>Conexão MCP verificada · ferramentas: {r.mcp.ferramentas.join(', ')}.</p>}
  </div>;
}

export default function OperationsPanel({ data, mode, onOpen, connected, checkedAt, now, job, available, canResume, local, sending, error, onStart, onStop }) {
  const [group, setGroup] = useState('auditoria');
  const selected = groups.find(g => g.id === group);
  const active = Boolean(job?.active);
  const otherRun = active && job.run_id !== data.id;
  const title = !connected ? 'Executor local indisponível' : active ? job.status === 'parando' ? 'Interrupção solicitada — aguardando a operação atual' : `${actionLabels[job.action] || 'Ação'} em andamento` : 'Nenhuma ação em andamento';
  if (mode !== 'full') {
    if (mode !== 'overview' && !active && !error) return null;
    return <section className={`execution-strip ${active ? 'is-active' : ''}`} aria-label="Acompanhamento da auditoria">
      {active ? <LoaderCircle size={19} className="spin" /> : <Activity size={19} />}
      <div><strong>{title}</strong><small>{otherRun ? `A ação pertence à execução ${job.run_id}.` : active ? 'O trabalho continua ao navegar pelo painel.' : job ? `Última ação: ${actionLabels[job.action]} · ${statuses[job.status] || job.status}.` : 'Acompanhe ou execute ações na área Operações.'}</small>{error && <p role="alert">{error}</p>}</div>
      {active && <button className="button outline small" onClick={onStop} disabled={sending || job.status === 'parando'}><Pause size={14} />{job.status === 'parando' ? 'Interrompendo...' : 'Interromper'}</button>}
      <button className="text-button" onClick={onOpen}>Ver operações <ArrowRight size={15} /></button>
    </section>;
  }
  function allowed(action) {
    if (!available) return false;
    if (action === 'nova_auditoria') return true;
    if (action === 'retomar_auditoria') return canResume;
    if (action === 'preparar_rag') return local && Boolean(data.documents);
    if (action === 'conferir_suporte') return local && Boolean(data.review?.itens?.length);
    return local && Boolean(data.audit);
  }
  function actionCard([action, Icon, description]) {
    return <button key={action} className={`operation-action ${action === 'nova_auditoria' ? 'primary-operation' : ''}`} disabled={!allowed(action)} onClick={() => onStart(action)}>
      <span className="operation-action-icon"><Icon size={21} /></span><span><strong>{actionLabels[action]}</strong><small>{description}</small></span><ArrowRight size={16} />
    </button>;
  }
  return <section className="run-controls operations-panel" aria-label="Executar ações da auditoria">
    <div className="operations-heading"><div><h2>O que você precisa fazer?</h2><p>Escolha uma etapa. As ações usam a execução selecionada acima.</p></div><span className={`executor-connection ${connected ? 'online' : ''}`}><span />{connected ? 'Executor conectado' : 'Executor indisponível'}</span></div>
    {active && <ExecutionStatus data={data} job={job} connected={connected} now={now} checkedAt={checkedAt} />}
    <div className="workspace-tabs" role="group" aria-label="Etapas das operações">{groups.map(g => <button key={g.id} aria-pressed={g.id === group} className={g.id === group ? 'selected' : ''} onClick={() => setGroup(g.id)}>{g.label}</button>)}</div>
    <p className="operation-guidance">{group === 'auditoria' ? 'Use Nova auditoria ou Retomar auditoria no topo dos escritórios. Essas ações usam IA e podem gravar os achados no banco.' : selected.note}</p>
    {!local && <p className="document-warning">Selecione uma execução local para consultar fontes e revisar os dados.</p>}
    {group !== 'auditoria' && <div className="operation-actions">{selected.actions.map(actionCard)}</div>}
    {error && <p className="run-error" role="alert"><CircleAlert size={16} />{error}</p>}
    {job && <details className={`operation-history job-${job.status}`} open={active || undefined}>
      <summary>{active ? <LoaderCircle size={17} className="spin" /> : job.status === 'concluido' ? <Check size={17} /> : <CircleAlert size={17} />}<span>{active ? 'Ação atual' : 'Última ação'}: {actionLabels[job.action]} · {statuses[job.status] || job.status}</span></summary>
      <div className="operation-history-body"><p className="muted">Execução {job.run_id}{job.finished_at && ` · ${new Date(job.finished_at).toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo'})}`}</p>
        {job.mensagem && <p role="alert">{job.mensagem}</p>}
        {job.status === 'parando' && <p>Aguardando a operação atual encerrar. Checkpoints concluídos serão preservados.</p>}
        <JobResult job={job} />
        {active && <button className="button outline small" onClick={onStop} disabled={sending || job.status === 'parando'}><Pause size={14} />{job.status === 'parando' ? 'Interrompendo...' : 'Interromper'}</button>}
        <details className="job-log"><summary><Terminal size={14} />Ver andamento e mensagens</summary><pre>{job.log || 'Aguardando as primeiras mensagens do executor...'}</pre></details>
      </div>
    </details>}
    <details className="operation-advanced"><summary>Ferramentas avançadas</summary><p>Prepare a busca após extrair documentos. A verificação de conexão é um diagnóstico local.</p><div className="operation-actions">{[['preparar_rag', FileSearch, 'Indexar os textos já extraídos para busca local.'], ['verificar_mcp', Activity, 'Testar a conexão das ferramentas de evidência.']].map(actionCard)}</div></details>
    <p className="operation-footnote">Navegar ou fechar a aba não interrompe o trabalho. Para parar uma ação, use Interromper.</p>
  </section>;
}
