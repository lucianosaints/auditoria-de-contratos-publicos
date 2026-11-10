export const officeAgents = [
  { name: 'Coletor', task: 'Busca contratos e organiza as fontes', color: '#56bdc6' },
  { name: 'Auditor', task: 'Analisa os contratos por lotes', color: '#9d8bf4' },
  { name: 'Arquivista', task: 'Preserva resultados e recibos', color: '#e4b66c' },
  { name: 'Investigador', task: 'Investiga alertas e reúne citações', color: '#79ba86' },
  { name: 'Revisor', task: 'Questiona achados e confere evidências', color: '#e594a4' },
];

export function officeState(data, job, connected) {
  if (!connected) return { index: -1, moving: false, label: 'Conexão com o executor indisponível' };
  if (job?.run_id !== data.id) return { index: -1, moving: false, label: job?.active ? 'Há trabalho em outra execução' : 'Equipe em espera' };
  if (!job?.active) return { index: -1, moving: false, label: job?.status === 'falhou' ? 'Execução encerrada com falha' : 'Equipe em espera' };
  let index = -1;
  const reported = job.office;
  const status = data.progress?.status;
  if (job.action === 'revisar_achados' || ['nova_auditoria', 'retomar_auditoria'].includes(job.action) && status === 'revisando_achados') {
    index = data.review?.etapa_atual === 'investigacao' ? 3 : data.review?.etapa_atual === 'revisao' ? 4 : -1;
  } else if (['nova_auditoria', 'retomar_auditoria'].includes(job.action)) {
    index = status === 'analisando' ? 1 : -1;
  }
  if (reported) index = Number.isInteger(reported.agent) && reported.agent >= 0 && reported.agent < 5 ? reported.agent : -1;
  const waiting = job.status === 'parando' || ['aguardando_intervalo', 'aguardando_cota'].includes(reported?.phase) || !reported && (['aguardando_intervalo', 'aguardando_cota'].includes(data.review?.fase_atual) && index >= 3 || ['aguardando_intervalo', 'aguardando_cota'].includes(data.progress?.fase_atual) && index === 1);
  return { index, moving: index >= 0 && !waiting, label: waiting ? 'Aguardando · animação pausada' : index >= 0 ? `${officeAgents[index].name} trabalhando` : 'Operação em andamento · etapa sem agente identificado' };
}

// Só entrega entre eventos consecutivos confirmados da mesma ação/execução.
// Ao abrir uma ação já em curso, começa no estado atual sem repetir o passado.
export function officeTransitions(cursor, job, runId) {
  const valid = job?.run_id === runId && (job.active || job.status === 'concluido');
  const events = Array.isArray(job?.office?.events) ? job.office.events.filter(e => Number.isInteger(e.seq) && Number.isInteger(e.agent) && e.agent >= 0 && e.agent < 5) : [];
  const key = valid ? `${runId}:${job.id}` : '';
  if (!key || cursor.key !== key) return { cursor: { key, seq: events.at(-1)?.seq || 0, agent: events.at(-1)?.agent ?? null }, deliveries: [], reset: true };
  const deliveries = [];
  let { seq, agent } = cursor;
  for (const event of events) {
    if (event.seq <= seq) continue;
    if (event.seq === seq + 1 && agent !== null && event.agent !== agent) deliveries.push({ from: agent, to: event.agent, seq: event.seq });
    seq = event.seq; agent = event.agent;
  }
  return { cursor: { key, seq, agent }, deliveries, reset: false };
}
