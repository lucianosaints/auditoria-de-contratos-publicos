export function indicatorState(data) {
  if (!data.indicators) return 'nao_preparado';
  return data.indicatorsCurrent === true && data.indicators.versao === 1 && !data.demo && data.id !== 'importado' ? 'pronto' : 'desatualizado';
}

export function exactBrl(raw) {
  if (typeof raw !== 'string' || !/^-?\d+\.\d{2}$/.test(raw)) return 'Não informado';
  const [whole, cents] = raw.split('.');
  return `R$ ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents}`;
}

export const coverageLabels = { valido: 'Formato monetário válido', ausente: 'Valor ausente', invalido: 'Formato monetário inválido',
  nao_processado: 'Documentos não processados', fonte_desatualizada: 'Fonte desatualizada',
  pdf_publicado_extraido: 'PDF publicado com texto extraído', somente_fichas_ou_sem_tipo_validado: 'Somente fichas ou tipo ainda não validado',
  sem_texto_extraido: 'Sem texto documental extraído', nao_consultado: 'PNCP não consultado',
  confirmado_por_regras: 'Vínculo PNCP confirmado por regras', candidato: 'Candidato PNCP', conflitante: 'Candidatos com diferenças',
  nao_localizado_no_recorte: 'Não localizado no recorte PNCP', consulta_incompleta: 'Consulta PNCP incompleta' };

export const issueLabels = { valor_ausente: 'Valor ausente', valor_invalido: 'Formato monetário inválido ou ambíguo',
  valor_negativo: 'Valor negativo exige identificar ajustes ou estornos',
  cnpj_fornecedor_ausente_ou_formato_invalido: 'Sem CNPJ de fornecedor no formato esperado',
  identidade_contratual_incompleta: 'Número/ano, processo ou CNPJ incompletos',
  objeto_ausente: 'Objeto não informado', identidade_contratual_repetida: 'Identidade contratual repetida na coleta' };
