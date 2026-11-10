import { useEffect, useRef, useState } from 'react';
import OperationsPanel from './OperationsPanel.jsx';
import AgentOffice from './AgentOffice.jsx';

export default function RunControls({ data, loading, onJobUpdate, mode = 'full', onOpen }) {
  const [control, setControl] = useState(null);
  const [job, setJob] = useState(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [connected, setConnected] = useState(false);
  const [checkedAt, setCheckedAt] = useState(null);
  const [now, setNow] = useState(Date.now());
  const callback = useRef(onJobUpdate);
  const lastNotification = useRef('');
  callback.current = onJobUpdate;
  const local = !data.demo && data.id !== 'importado';
  const busy = sending || Boolean(job?.active) || Boolean(control?.jobs?.some(j => j.active));
  const available = connected && !busy && !loading;
  const canResume = local && data.records.length > 0 && !(data.receipt?.ok && data.progress?.status === 'concluido');
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);

  useEffect(() => {
    let cancelled = false;
    let timer;
    async function poll() {
      try {
        const response = await fetch('/api/control');
        if (!response.ok) throw new Error('Controles indisponíveis. Reabra o painel pelo iniciar_painel.bat.');
        const state = await response.json();
        if (cancelled) return;
        if (!Array.isArray(state.jobs) || typeof state.token !== 'string') throw new Error('Executor local indisponível.');
        setControl(state); setConnected(true); setCheckedAt(Date.now());
        const current = state.jobs.find(j => j.active) || state.jobs[0];
        if (current) {
          const details = await fetch(`/api/jobs/${encodeURIComponent(current.id)}`).then(r => r.ok ? r.json() : null);
          if (cancelled) return;
          setJob(details || current);
          const key = `${current.id}:${current.status}:${current.finished_at || Math.floor(Date.now() / 6000)}`;
          if (key !== lastNotification.current) {
            lastNotification.current = key;
            callback.current?.(details || current);
          }
        } else setJob(null);
      } catch { if (!cancelled) setConnected(false); }
      finally { if (!cancelled) timer = setTimeout(poll, 3000); }
    }
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, []);

  async function start(action) {
    if (!available) return;
    setSending(true); setError('');
    try {
      const response = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Audit-Control': control.token },
        body: JSON.stringify({ action, ...(action === 'nova_auditoria' ? {} : { runId: data.id }) }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Não foi possível iniciar a ação.');
      setJob(result);
      setControl(c => ({ ...c, jobs: [result, ...(c?.jobs || []).filter(j => j.id !== result.id)] }));
      lastNotification.current = '';
      callback.current?.(result, true);
    } catch (e) { setError(e.message); }
    finally { setSending(false); }
  }

  async function stop() {
    setSending(true); setError('');
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(job.id)}/stop`, { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Audit-Control': control.token }, body: '{}' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Não foi possível interromper.');
      setJob(result);
    } catch (e) { setError(e.message); }
    finally { setSending(false); }
  }
  return <>{['overview', 'full'].includes(mode) && <AgentOffice data={data} job={job} connected={connected} available={available} canResume={canResume} sending={sending} error={error} onStart={() => start('nova_auditoria')} onResume={() => start('retomar_auditoria')} />}<OperationsPanel data={data} mode={mode} onOpen={onOpen} connected={connected} checkedAt={checkedAt} now={now}
    job={job} available={available} canResume={canResume} local={local} sending={sending} error={error} onStart={start} onStop={stop} /></>;
}
