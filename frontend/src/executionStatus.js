export const actionLabels = { nova_auditoria: 'Nova auditoria', retomar_auditoria: 'Retomar auditoria',
  consultar_diario: 'Consultar Diário', revisar_achados: 'Revisar com agentes', planejar_revisao: 'Estimar revisão',
  planejar_documentos: 'Planejar documentos', coletar_documentos: 'Ler documentos', preparar_rag: 'Preparar RAG', verificar_mcp: 'Verificar MCP', conferir_suporte: 'Conferir suporte', consultar_pncp: 'Consultar PNCP', gerar_indicadores: 'Gerar indicadores', consultar_financeiro: 'Consultar financeiro' };

export function failureExplanation(error) {
  const text = String(error || '');
  if (/WinError (?:5|32|33)|PermissionError|acesso negado|permission denied|sharing violation/i.test(text)) return 'O Windows impediu a gravação de um arquivo de progresso. Os checkpoints concluídos foram preservados; a retomada reaproveita os contratos compatíveis.';
  if (/Expecting value|JSON inválido|JSON válido|Formato da resposta inválido|JSONDecodeError/i.test(text)) return 'Não foi possível ler o JSON da resposta da IA. O texto original foi preservado para diagnóstico; a auditoria base continua concluída.';
  if (/at most 700 characters|string_too_long/.test(text)) return 'A IA enviou uma citação maior que o limite permitido. Os contratos já revisados foram preservados; a etapa pendente precisa selecionar trechos do catálogo.';
  if (/citacao_id/.test(text)) return 'A IA selecionou uma referência que não corresponde ao catálogo permitido deste contrato. As evidências não foram aceitas e os resultados concluídos foram preservados.';
  if (/at least 8 characters|string_too_short|citação curta/.test(text)) return 'A IA devolveu uma citação curta sem o campo completo exigido. A revisão foi interrompida para preservar a validação das evidências.';
  if (/citação|citation|structured output|validation error|validar/i.test(text)) return 'A resposta da IA não passou na validação das evidências. A revisão foi interrompida; os resultados anteriores foram preservados.';
  if (/quota|429|rate.?limit/i.test(text)) return 'O provedor de IA limitou as chamadas. A execução parou e os checkpoints concluídos foram preservados.';
  return 'A etapa não foi concluída. Consulte as mensagens da execução para conferir o motivo antes de tentar novamente.';
}

const phases = { aguardando_intervalo: 'Pausa entre chamadas à IA', aguardando_cota: 'Aguardando cota do provedor',
  chamando_ia: 'Aguardando resposta da IA', consolidando: 'Consolidando resultados' };
export function executionStatus(data, job, connected) {
  const same = job?.run_id === data.id;
  const active = Boolean(job?.active);
  const reviewAction = job?.action === 'revisar_achados' || ['nova_auditoria', 'retomar_auditoria'].includes(job?.action) && data.progress?.status === 'revisando_achados';
  const state = same && active ? reviewAction ? data.review : job?.action === 'coletar_documentos' ? data.documents : job?.action === 'consultar_financeiro' ? (data.financialCurrent ? data.financial : null) : job?.action === 'consultar_pncp' ? data.pncp : job?.action === 'gerar_indicadores' ? null : data.progress : null;
  let title = !connected ? 'Não foi possível confirmar o executor local' : active ? `${actionLabels[job.action] || 'Ação'} em andamento` : 'Nenhuma ação em andamento';
  if (connected && job?.status === 'parando') title = 'Interrupção solicitada — aguardando a operação atual';
  const details = [];
  if (active) {
    if (!same) details.push(`A ação está na execução ${job.run_id}; os dados selecionados são de outra execução.`);
    else if (reviewAction) {
      const stage = state?.etapa_atual === 'investigacao' ? 'Investigador' : state?.etapa_atual === 'revisao' ? 'Revisor' : 'Preparação';
      details.push(`Revisão: ${state?.itens?.length ?? 0}/${state?.total_contratos ?? 0} contratos · ${state?.lotes_concluidos ?? 0}/${state?.total_lotes ?? 0} lotes concluídos${state?.lote_atual ? ` · lote atual ${state.lote_atual}` : ''} · ${stage}.`);
      details.push(phases[state?.fase_atual] || 'Preparando a etapa ou aguardando o intervalo entre chamadas.');
    } else if (job.action === 'coletar_documentos') details.push(`Documentos: ${state?.documentos_processados ?? 0}/${state?.planejamento?.documentos ?? 0} processados.`);
    else if (job.action === 'consultar_financeiro') details.push(state?.status === 'em_andamento' ? `Financeiro: ${state.processados ?? 0}/${state.linhas?.length ?? 0} contratos. Até 10 consultas por CNPJ/exercício e 30 detalhes; sem IA ou banco.` : 'Consultando empenhos e conferindo identidades. Até 10 consultas por CNPJ/exercício e 30 detalhes; sem IA ou banco.');
    else if (job.action === 'gerar_indicadores') details.push('Calculando cobertura e distribuição dos valores da coleta local com pandas. Sem IA, rede ou banco.');
    else if (job.action === 'consultar_pncp') details.push(state?.status === 'em_andamento' ? `PNCP: ${state.processados ?? 0}/${state.linhas?.length ?? 0} contratos conferidos; consulte as mensagens para a paginação.` : 'Consultando catálogo público e identificadores do PNCP. Sem IA ou banco.');
    else if (['nova_auditoria', 'retomar_auditoria'].includes(job.action)) {
      details.push(data.progress?.status === 'consultando_diario' ? 'Consultando publicações no Diário Oficial.' : state?.total_lotes ? `Auditoria: ${state.lotes_concluidos ?? 0}/${state.total_lotes} lotes · ${state.linhas_concluidas ?? 0}/${state.total_contratos ?? data.records.length} contratos analisados.` : 'Coletando contratos e detalhes do portal. Esta etapa pode levar alguns minutos.');
      if (phases[state?.fase_atual]) details.push(phases[state.fase_atual]);
    }
  } else if (same && job) details.push(`Última ação: ${actionLabels[job.action] || job.action} · ${job.status === 'falhou' ? 'falhou' : job.status === 'concluido' ? 'concluída' : 'interrompida'}.`);
  if (data.progress?.status === 'concluido') details.push(`Auditoria base concluída: ${data.progress.linhas_concluidas ?? data.records.length} contratos analisados · ${data.progress.lotes_concluidos ?? 0}/${data.progress.total_lotes ?? 0} lotes.${data.receipt?.ok ? ` Recibo confirma ${data.receipt.recebidos ?? data.receipt.contratos_localizados ?? 0} contratos arquivados.` : ''}`);
  const failedReview = !active && data.review?.status === 'interrompida';
  if (failedReview) details.push(`Revisão adicional interrompida: ${data.review.itens?.length ?? 0}/${data.review.total_contratos ?? 0} contratos revisados · ${data.review.lotes_concluidos ?? 0}/${data.review.total_lotes ?? 0} lotes concluídos.`);
  const failure = failedReview ? failureExplanation(data.review.erro) : same && job?.status === 'falhou' ? job.mensagem || failureExplanation() : null;
  return { title, details, failure, active, phase: state?.fase_atual, waitUntil: state?.espera_ate,
    progress: active && same && state ? ['consultar_pncp', 'consultar_financeiro'].includes(job.action) ?
      (state.status === 'em_andamento' ? { value: state.processados ?? 0, total: state.linhas?.length ?? 0 } : null) : job.action === 'coletar_documentos' ?
      { value: state.documentos_processados ?? 0, total: state.planejamento?.documentos ?? 0 } :
      { value: state.lotes_concluidos ?? 0, total: state.total_lotes ?? 0 } : null };
}

export function elapsedTime(start, end) {
  const seconds = Math.max(0, Math.floor((end - Date.parse(start)) / 1000));
  if (!Number.isFinite(seconds)) return '';
  return seconds >= 3600 ? `${Math.floor(seconds / 3600)}h ${Math.floor(seconds % 3600 / 60)}min` : `${Math.floor(seconds / 60)}min ${seconds % 60}s`;
}
