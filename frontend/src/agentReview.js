export const reviewLabels = {
  contextualizado: 'Alerta contextualizado',
  necessita_documentos: 'Documentos necessários',
  rever_alerta: 'Alerta precisa de revisão',
};

const string = value => typeof value === 'string' && value.trim().length > 0;
const strings = value => Array.isArray(value) && value.every(string);
const record = value => value && typeof value === 'object' && !Array.isArray(value) && Object.values(value).every(v => typeof v === 'string');
const ordered = value => JSON.stringify(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)));

export function validateAgentReview(review) {
  if (!review) return;
  if (!['em_andamento', 'concluida', 'interrompida', 'sem_achados'].includes(review.status) ||
      !string(review.nota) || !Number.isInteger(review.total_contratos) || review.total_contratos < 0 ||
      !Array.isArray(review.itens) || new Set(review.itens.map(i => i?.linha)).size !== review.itens.length ||
      review.itens.length > review.total_contratos ||
      !review.itens.every(item => item && Number.isInteger(item.linha) && item.linha > 0 &&
        Object.hasOwn(reviewLabels, item.situacao) && string(item.explicacao_simples) && string(item.limite) && string(item.proxima_diligencia) &&
        strings(item.skills) && record(item.registro_original) && strings(item.motivos_originais) && item.motivos_originais.length > 0 &&
        Array.isArray(item.evidencias) && item.evidencias.length > 0 && item.evidencias.every(e => e && string(e.fonte_id) &&
          e.fonte_id.startsWith(`L${item.linha}-`) && string(e.trecho) && e.fonte && string(e.fonte.rotulo) &&
          string(e.fonte.texto) && e.fonte.texto.includes(e.trecho) && e.trecho.length <= 700 &&
          (e.trecho.length >= 8 || (e.fonte.tipo === 'campo_portal' && !e.fonte.truncado && e.trecho === e.fonte.texto.trim())) &&
          (!e.fonte.pagina || (Number.isInteger(e.fonte.pagina) && e.fonte.pagina > 0)) &&
          (e.fonte.url == null || typeof e.fonte.url === 'string')))) {
    throw new Error('revisao_agentes.json não tem a estrutura esperada ou contém citações inválidas.');
  }
}

export function reviewState(data) {
  const review = data.review;
  if (!review) return { items: [], stale: 0, status: 'nao_realizada' };
  const gazetteChanged = (review.diario_assinatura ?? null) !== (data.gazette?.assinatura ?? null) ||
    (review.diario_consultado_em ?? null) !== (data.gazette?.consultado_em ?? null);
  const documentsChanged = (review.documentos_assinatura ?? null) !== (data.documents?.assinatura ?? null);
  const items = review.itens.filter(item => {
    const original = data.records[item.linha - 1];
    const reasons = [...new Set((data.audit?.suspeitos || []).filter(f => f.linha === item.linha).map(f => f.motivo_suspeita))];
    return !gazetteChanged && !documentsChanged && original && ordered(item.registro_original) === ordered(original) &&
      JSON.stringify([...item.motivos_originais].sort()) === JSON.stringify(reasons.sort());
  });
  return { items, stale: review.itens.length - items.length, status: review.status };
}
