import { ChartNoAxesCombined } from 'lucide-react';
import { coverageLabels, exactBrl, indicatorState, issueLabels } from './indicators.js';

export function IndicatorsOverview({ data, onOpenLine }) {
  const state = indicatorState(data);
  if (state === 'nao_preparado') return null;
  if (state !== 'pronto') return <section className="agent-overview" aria-label="Indicadores de gestão"><ChartNoAxesCombined size={24} /><div><strong>Indicadores precisam ser atualizados</strong><p>As fontes ou os indicadores mudaram. Use Gerar indicadores para calcular com os dados atuais.</p></div></section>;
  const result = data.indicators;
  const summary = result.resumo;
  return <section className="analytics-panel" aria-label="Indicadores de gestão"><div className="simple-summary-label"><ChartNoAxesCombined size={18} />INDICADORES DA COLETA</div>
    <h2>Valores contratuais e cobertura das fontes</h2><p className="muted">Cálculos locais com pandas, em {new Date(result.gerado_em).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}. Os valores representam contratos, sem comprovação de pagamento ou entrega.</p>
    <div className="analytics-metrics">
      <div><span>Linhas elegíveis</span><strong>{summary.linhas_elegiveis_distribuicao} / {summary.linhas_coletadas}</strong></div>
      <div><span>Valor contratual elegível</span><strong>{exactBrl(summary.valor_contratual_elegivel)}</strong></div>
      <div><span>Linhas excluídas da distribuição</span><strong>{summary.linhas_excluidas_distribuicao}</strong></div>
      <div><span>Participação dos cinco maiores</span><strong>{summary.participacao_cinco_maiores_percentual == null ? 'Não calculável' : `${summary.participacao_cinco_maiores_percentual.replace('.', ',')}%`}</strong></div>
    </div>
    <p className="simple-note">{result.metodologia.denominador} {result.metodologia.exclusoes} {summary.linhas_identidade_repetida} linhas têm identidade repetida.</p>
    <div className="analytics-coverage">{Object.entries(result.cobertura).map(([group, counts]) => <div key={group}><h3>{({ valores: 'Qualidade dos valores', documentos: 'Cobertura documental', pncp: 'Cobertura PNCP' })[group]}</h3><dl>{Object.entries(counts).map(([key, count]) => <div key={key}><dt>{coverageLabels[key] || key}</dt><dd>{count}</dd></div>)}</dl></div>)}</div>
    <details className="analytics-suppliers"><summary>Distribuição entre fornecedores ({summary.fornecedores_no_recorte_elegivel} no recorte elegível)</summary>
      <p className="muted">Contratados e beneficiários conforme o cadastro; o recorte pode incluir convênios e ajustes de naturezas diferentes. Agrupamento por CNPJ, preservando zeros iniciais. Nomes iguais não bastam para unir registros. Os dez maiores valores estão abaixo; cada linha abre o registro da coleta.</p>
      <div className="table-scroll"><table><thead><tr><th>Fornecedor / CNPJ</th><th>Linhas elegíveis</th><th>Valor contratual</th><th>Participação</th></tr></thead><tbody>{result.fornecedores.slice(0, 10).map(s => <tr key={s.cnpj}><td>{s.nomes_publicados.join(' / ') || 'Nome não informado'}<small>{s.cnpj}</small></td><td>{s.linhas.slice(0, 6).map(line => <button className="text-button" key={line} onClick={() => onOpenLine?.(line)}>Linha {line}</button>)}{s.linhas.length > 6 && <small>+ {s.linhas.length - 6} linhas</small>}</td><td>{exactBrl(s.valor_contratual)}</td><td>{s.participacao_percentual == null ? 'Não calculável' : `${s.participacao_percentual.replace('.', ',')}%`}</td></tr>)}</tbody></table></div>
    </details>
    <p className="document-warning">Execução financeira: não avaliável. {result.execucao_financeira.motivo}</p><p className="simple-note">{result.limite}</p>
  </section>;
}

export function IndicatorDetails({ data, line }) {
  if (indicatorState(data) !== 'pronto') return null;
  const item = data.indicators.itens.find(i => i.linha === line);
  if (!item) return null;
  return <section className="document-dossier" aria-label="Indicadores deste contrato"><div className="simple-summary-label"><ChartNoAxesCombined size={18} />DADOS E INDICADORES</div>
    <p>Valor usado: {exactBrl(item.valor_contratual)} · campo: {item.campo_valor || 'não informado'}.</p>
    <p>{item.elegivel_distribuicao ? 'Incluído na distribuição de valores contratuais por fornecedor.' : 'Excluído da distribuição por identidade ou valor insuficiente, repetido ou incompatível.'}</p>
    {item.avisos_dados.map(code => <p className="document-warning" key={code}>{issueLabels[code] || code}.</p>)}
    <p>{coverageLabels[item.cobertura_documental] || item.cobertura_documental} · {coverageLabels[item.situacao_pncp] || item.situacao_pncp}.</p>
    <p className="simple-note">Ausência de aviso não valida a regularidade ou a entrega. A elegibilidade é um critério do cálculo, sem classificação de risco.</p>
  </section>;
}
