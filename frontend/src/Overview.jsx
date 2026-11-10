import { useState, useEffect } from 'react';
import { 
  ArrowRight, 
  Building2, 
  ChartNoAxesCombined, 
  Check, 
  CheckCircle2, 
  CircleAlert, 
  ClipboardCheck, 
  ExternalLink, 
  FileText, 
  FolderOpen, 
  Globe, 
  RotateCcw, 
  Save, 
  Sparkles, 
  TriangleAlert 
} from 'lucide-react';

function isECidadeUrl(url) {
  if (!url) return false;
  const lower = url.toLowerCase();
  return lower.includes('e-cidade') || lower.includes('/contratos/padrao') || lower.includes('ipm.com.br');
}

export function PortalConfigCard({ portalConfig, onSavePortalConfig, onResetPortalConfig }) {
  const [urlInput, setUrlInput] = useState(portalConfig?.url || '');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (portalConfig?.url) {
      setUrlInput(portalConfig.url);
    }
  }, [portalConfig?.url]);

  const ecidade = isECidadeUrl(urlInput);

  async function handleSave(e) {
    e?.preventDefault();
    if (!urlInput.trim()) return;
    setSaving(true);
    setFeedback(null);
    try {
      await onSavePortalConfig(urlInput.trim());
      setFeedback({ type: 'success', message: 'Portal da transparência atualizado com sucesso!' });
      setTimeout(() => setFeedback(null), 4000);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Erro ao salvar a URL do portal.' });
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    setSaving(true);
    setFeedback(null);
    try {
      await onResetPortalConfig();
      setFeedback({ type: 'success', message: 'Restaurado para o portal padrão (Maricá - RJ).' });
      setTimeout(() => setFeedback(null), 4000);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Erro ao restaurar o portal padrão.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="portal-config-card" aria-label="Configuração do Portal da Transparência">
      <div className="portal-config-header">
        <div className="portal-config-title-group">
          <div className="portal-config-icon">
            <Building2 size={22} />
          </div>
          <div>
            <h2>Portal da Transparência da sua Cidade</h2>
            <p>Informe o link do portal da transparência do seu município para coletar e auditar os contratos da prefeitura.</p>
          </div>
        </div>
        <div className="portal-city-pill" title="Município ativo no observatório">
          <span className="dot" />
          <span>{portalConfig?.name || 'Maricá - RJ'}</span>
        </div>
      </div>

      <form className="portal-config-form" onSubmit={handleSave}>
        <div className="portal-input-row">
          <div className="portal-input-wrapper">
            <Globe size={18} />
            <input
              type="url"
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              placeholder="https://transparencia.suacidade.uf.gov.br/e-cidade/contratos/padrao"
              aria-label="Link do portal da transparência"
              required
            />
          </div>
          <div className="portal-actions-row">
            <button 
              type="submit" 
              className="button primary" 
              disabled={saving || !urlInput.trim() || urlInput.trim() === portalConfig?.url}
            >
              <Save size={16} />
              {saving ? 'Salvando...' : 'Salvar e Definir Alvo'}
            </button>
            {portalConfig?.custom && (
              <button 
                type="button" 
                className="button outline" 
                onClick={handleReset} 
                disabled={saving}
                title="Voltar para a configuração de Maricá - RJ"
              >
                <RotateCcw size={16} />
                Restaurar Padrão
              </button>
            )}
            {urlInput && (
              <a 
                href={urlInput} 
                target="_blank" 
                rel="noreferrer" 
                className="button outline" 
                title="Abrir o portal em uma nova aba para conferir"
              >
                <ExternalLink size={16} />
                Testar Acesso
              </a>
            )}
          </div>
        </div>

        {feedback && (
          <div className={feedback.type === 'success' ? 'portal-success-msg' : 'error-notice'} role="status">
            {feedback.type === 'success' ? <Check size={16} /> : <CircleAlert size={16} />}
            <span>{feedback.message}</span>
          </div>
        )}

        <div className={`portal-status-box ${ecidade ? 'ecidade' : 'warning'}`}>
          {ecidade ? <CheckCircle2 size={18} /> : <TriangleAlert size={18} />}
          <div>
            <strong>
              {ecidade ? 'Plataforma e-Cidade detectada (Compatível)' : 'Outra plataforma ou portal municipal detectado'}
            </strong>
            <p>
              {ecidade
                ? 'Este endereço segue a estrutura e-Cidade (IPM Sistemas), o mesmo formato do coletor automatizado. A extração dos contratos, paginação e detalhes funcionará diretamente na opção "Nova auditoria".'
                : 'Cada prefeitura pode utilizar uma plataforma diferente (Betha, GOVBR, sistemas próprios). O sistema registrará este link como fonte oficial da sua cidade. Para portais com estrutura HTML diferente do e-Cidade, a coleta automatizada pode exigir adaptadores específicos.'}
            </p>
          </div>
        </div>
      </form>
    </section>
  );
}

export default function Overview({ 
  rows, 
  flagged, 
  review, 
  coverage, 
  onFlagged, 
  onNavigate,
  portalConfig,
  onSavePortalConfig,
  onResetPortalConfig 
}) {
  const metrics = [
    [FileText, 'Contratos na coleta', rows.length.toLocaleString('pt-BR'), 'Registros desta execução'],
    [CircleAlert, 'Com alertas', flagged.length.toLocaleString('pt-BR'), 'Para conferência humana'],
    [ClipboardCheck, 'Revisados pelos agentes', review.items.length.toLocaleString('pt-BR'), 'Compatíveis com as fontes atuais'],
    [ChartNoAxesCombined, 'Cobertura declarada', `${coverage}%`, 'Linhas declaradas como analisadas'],
  ];

  return (
    <div className="overview-workspace">
      <PortalConfigCard 
        portalConfig={portalConfig} 
        onSavePortalConfig={onSavePortalConfig} 
        onResetPortalConfig={onResetPortalConfig} 
      />

      <section className="metrics-grid" aria-label="Indicadores da execução">
        {metrics.map(([Icon, label, value, note]) => (
          <article className="metric" key={label}>
            <div className="metric-top">
              <span>{label}</span>
              <Icon size={18} />
            </div>
            <strong>{value}</strong>
            <small>{note}</small>
          </article>
        ))}
      </section>

      <section className="overview-next" aria-label="Próximo passo da análise">
        <div>
          <span className="section-kicker">PRÓXIMO PASSO</span>
          <h2>{flagged.length ? `${flagged.length} registros para olhar com atenção` : 'Explore os contratos e suas fontes'}</h2>
          <p>Abra um contrato para ler o alerta, conferir os documentos e registrar sua análise. Os indícios precisam ser avaliados junto das evidências.</p>
        </div>
        <button className="button primary" onClick={onFlagged}>
          {flagged.length ? 'Conferir alertas' : 'Explorar contratos'}
          <ArrowRight size={17} />
        </button>
      </section>

      <section className="overview-links" aria-label="Explorar a auditoria">
        {[
          ['evidence', FolderOpen, 'Consultar evidências', 'Documentos, PNCP e empenhos em um só lugar.'],
          ['indicators', ChartNoAxesCombined, 'Explorar indicadores', 'Cobertura e valores contratuais por fornecedor.'],
          ['report', FileText, 'Ler relatório', 'Parecer completo e informações da execução.'],
        ].map(([id, Icon, title, note]) => (
          <button key={id} onClick={() => onNavigate(id)}>
            <Icon size={23} />
            <strong>{title}</strong>
            <span>{note}</span>
            <ArrowRight size={17} />
          </button>
        ))}
      </section>
    </div>
  );
}
