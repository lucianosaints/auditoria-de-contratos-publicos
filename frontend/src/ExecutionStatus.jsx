import { Activity, CircleAlert, LoaderCircle } from 'lucide-react';
import { elapsedTime, executionStatus } from './executionStatus.js';

export default function ExecutionStatus({ data, job, connected, now, checkedAt }) {
  const state = executionStatus(data, job, connected);
  const remaining = state.waitUntil ? Math.max(0, Math.ceil((Date.parse(state.waitUntil) - now) / 1000)) : 0;
  return <div className={`execution-summary ${state.failure ? 'failed' : state.active ? 'running' : ''}`} aria-label="Estado atual da execução" role="status" aria-live="polite">
    <div className="execution-summary-title">{state.active && connected ? <LoaderCircle size={21} className="spin" /> : state.failure ? <CircleAlert size={21} /> : <Activity size={21} />}<strong>{state.title}</strong>
      {state.active && <span>Tempo decorrido: {elapsedTime(job.started_at || job.created_at, now)}</span>}
    </div>
    {state.details.map((text, i) => <p key={i}>{text}</p>)}
    {remaining > 0 && connected && state.active && <p>Próxima tentativa em aproximadamente {remaining}s.</p>}
    {state.progress?.total > 0 && <progress aria-label="Lotes ou documentos concluídos" value={state.progress.value} max={state.progress.total} />}
    {state.failure && <p className="execution-failure"><strong>Motivo da parada:</strong> {state.failure}</p>}
    {job && !job.active && job.finished_at && <small>Última ação encerrada em {new Date(job.finished_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}.</small>}
    <small>{connected && checkedAt ? `Executor verificado às ${new Date(checkedAt).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo' })}. Atualização automática a cada 3 segundos.` : 'A conexão com o executor precisa ser restabelecida para confirmar se há trabalho ativo.'}</small>
  </div>;
}
