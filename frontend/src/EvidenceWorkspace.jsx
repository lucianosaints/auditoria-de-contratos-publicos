import { useState } from 'react';
import { DocumentsOverview } from './Documents.jsx';
import { PncpOverview } from './Pncp.jsx';
import { FinancialOverview } from './Financial.jsx';
import RagSearch from './RagSearch.jsx';

const tabs = [{ id: 'documents', label: 'Documentos' }, { id: 'pncp', label: 'PNCP' },
  { id: 'financial', label: 'Financeiro' }, { id: 'search', label: 'Busca local' }];

export default function EvidenceWorkspace({ data, onOpenLine, onOperations }) {
  const [tab, setTab] = useState('documents');
  function keydown(event, index) {
    const direction = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : direction ? (index + direction + tabs.length) % tabs.length : null;
    if (next !== null) { event.preventDefault(); setTab(tabs[next].id); document.getElementById(`source-tab-${tabs[next].id}`)?.focus(); }
  }
  const missing = tab === 'documents' ? !data.documents : tab === 'pncp' ? !data.pncp : tab === 'financial' ? !data.financial : false;
  return <section className="evidence-workspace" aria-label="Fontes e evidências">
    <div className="workspace-tabs" role="tablist" aria-label="Tipo de evidência">{tabs.map((t, i) => <button role="tab" id={`source-tab-${t.id}`} key={t.id} tabIndex={tab === t.id ? 0 : -1} aria-selected={tab === t.id} aria-controls={`source-panel-${t.id}`} onKeyDown={e => keydown(e, i)} onClick={() => setTab(t.id)}>{t.label}</button>)}</div>
    <div role="tabpanel" id={`source-panel-${tab}`} aria-labelledby={`source-tab-${tab}`}>
      <div className="workspace-help"><p>Consulte os resultados salvos. Para buscar ou atualizar fontes, use as operações.</p><button className="text-button" onClick={onOperations}>Abrir operações</button></div>
      {missing ? <div className="workspace-empty"><h2>Esta fonte ainda não foi consultada</h2><p>Use as ações em Operações para preparar os dados desta execução.</p></div> : <>
        {tab === 'documents' && <><DocumentsOverview data={data} /><p className="workspace-note">Os documentos e as páginas de origem estão nos detalhes de cada contrato.</p></>}
        {tab === 'pncp' && <PncpOverview data={data} />}
        {tab === 'financial' && <FinancialOverview data={data} onOpenLine={onOpenLine} />}
        {tab === 'search' && (!data.demo && data.id !== 'importado' ? <RagSearch key={data.id} data={data} /> : <div className="workspace-empty"><h2>Busca disponível nas execuções locais</h2><p>Selecione uma execução local para pesquisar seus documentos.</p></div>)}
      </>}
    </div>
  </section>;
}
