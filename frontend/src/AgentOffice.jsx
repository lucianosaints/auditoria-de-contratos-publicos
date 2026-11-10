import { useEffect, useRef, useState } from 'react';
import { Play, LoaderCircle, RefreshCw } from 'lucide-react';
import { officeAgents, officeState, officeTransitions } from './agentOffice.js';
import CollectorSources from './CollectorSources.jsx';

const desks = [[115, 132], [360, 132], [605, 132], [270, 330], [515, 330]];
const rooms = [
  { x: 48, y: 66, w: 232, h: 164, door: 151, top: true },
  { x: 293, y: 66, w: 232, h: 164, door: 396, top: true },
  { x: 538, y: 66, w: 254, h: 164, door: 641, top: true },
  { x: 154, y: 302, w: 250, h: 146, door: 189, top: false },
  { x: 416, y: 302, w: 250, h: 146, door: 451, top: false },
];
function GearIcon({ color = '#56bdc6', clockwise = true, size = 1, speed = '2.4s' }) {
  return (
    <g transform={`scale(${size})`}>
      <g>
        <animateTransform
          attributeName="transform"
          type="rotate"
          from={clockwise ? '0 0 0' : '360 0 0'}
          to={clockwise ? '360 0 0' : '0 0 0'}
          dur={speed}
          repeatCount="indefinite"
        />
        {/* 8 Dentes simétricos em cruz e diagonais */}
        <rect x="-2.2" y="-9.5" width="4.4" height="19" rx="1.2" fill={color} />
        <rect x="-9.5" y="-2.2" width="19" height="4.4" rx="1.2" fill={color} />
        <rect x="-2.2" y="-9.5" width="4.4" height="19" rx="1.2" fill={color} transform="rotate(45)" />
        <rect x="-2.2" y="-9.5" width="4.4" height="19" rx="1.2" fill={color} transform="rotate(-45)" />
        {/* Anel central */}
        <circle cx="0" cy="0" r="7" fill={color} />
        <circle cx="0" cy="0" r="4.8" fill="none" stroke="#ffffff" strokeWidth="0.8" opacity="0.35" />
        <circle cx="0" cy="0" r="2.8" fill="#111c29" />
      </g>
    </g>
  );
}

function Person({ x, y, color, working, walking = false, carrying = false }) {
  return <g transform={`translate(${x} ${y})`} className={`office-person ${working ? 'working' : ''} ${walking ? 'walking' : ''}`}>
    <ellipse cy="24" rx="13" ry="5" fill="#13212e" opacity=".3" />
    <path className="office-leg left" d="M-5 13v12" stroke="#263348" strokeWidth="6" />
    <path className="office-leg right" d="M5 13v12" stroke="#263348" strokeWidth="6" />
    <rect x="-12" y="-3" width="24" height="21" rx="5" fill={color} />
    <rect x="-9" y="-23" width="18" height="22" rx="7" fill="#ecc5a1" />
    <path d="M-10-14v-10h20v9H5v-5H-5v6Z" fill="#3b3442" />
    <path className="office-arm" d="M-13 2v12" stroke="#ecc5a1" strokeWidth="5" />
    <path d={carrying ? 'M13 2l9 6' : 'M13 2v12'} stroke="#ecc5a1" strokeWidth="5" />
    {carrying && (
      <g transform="translate(17 -4)" className="office-held-document">
        <rect width="16" height="21" rx="2" fill="#fff2cb" stroke="#d8b463" strokeWidth="2" />
        <path d="M4 6h8M4 10h8M4 14h6" stroke="#829394" strokeWidth="1.5" />
      </g>
    )}
    {working && (
      <>
        {/* Engrenagem girando no próprio peito do bonequinho */}
        <g transform="translate(0 7)">
          <GearIcon color="#ffd166" clockwise={true} size={0.52} speed="2s" />
        </g>
        {/* Balão de engrenagens em rotação ativa sobre o boneco */}
        <g className="person-working-indicator" transform="translate(14 -32)">
          <ellipse cx="0" cy="0" rx="17" ry="14" fill="#000000" opacity="0.45" />
          <rect x="-16" y="-14" width="32" height="28" rx="14" fill="#112231" stroke={color} strokeWidth="1.8" />
          <path d="M-6 13 L-10 18 L-2 13 Z" fill="#112231" stroke={color} strokeWidth="1" />
          {/* Engrenagem secundária dourada */}
          <g transform="translate(-6 -2)">
            <GearIcon color="#f6c343" clockwise={false} size={0.68} speed="1.9s" />
          </g>
          {/* Engrenagem primária com a cor do agente */}
          <g transform="translate(6 3)">
            <GearIcon color={color} clockwise={true} size={0.86} speed="2.5s" />
          </g>
          {/* Luz verde piscante de atividade confirmada */}
          <circle cx="10" cy="-9" r="2.2" fill="#4ade80">
            <animate attributeName="opacity" values="0.25;1;0.25" dur="1.2s" repeatCount="indefinite" />
          </circle>
        </g>
      </>
    )}
  </g>;
}
const home = i => [desks[i][0] + 36, desks[i][1] + 51];
function deliveryRoute(i, next = (i + 1) % desks.length) {
  const start = home(i), end = home(next);
  const from = rooms[i], to = rooms[next];
  const exit = from.top ? [[start[0], 207], [from.door, 207]] : [[start[0], 416], [from.door, 416]];
  const entry = to.top ? [[to.door, 207], [end[0]-30, 207]] : [[to.door, 416], [end[0]-30, 416]];
  return [start, ...exit, [from.door, 266], [to.door, 266], ...entry, [end[0]-30, end[1]]];
}
function alongRoute(points, fraction) {
  const lengths = points.slice(1).map((p, i) => Math.hypot(p[0]-points[i][0], p[1]-points[i][1]));
  let distance = Math.min(1, Math.max(0, fraction)) * lengths.reduce((a,b) => a+b, 0);
  for (let i=0; i<lengths.length; i++) {
    if (distance <= lengths[i]) { const t = lengths[i] ? distance / lengths[i] : 0; return points[i].map((v,j) => v + (points[i+1][j]-v)*t); }
    distance -= lengths[i];
  }
  return points.at(-1);
}
const DELIVERY_DURATION = 4000;

export default function AgentOffice({ data, job, connected, available, canResume, sending, error, onStart, onResume }) {
  const [preview, setPreview] = useState(false);
  const [step, setStep] = useState(0);
  const [travel, setTravel] = useState(0);
  const [deliveries, setDeliveries] = useState([]);
  const cursor = useRef({ key: '', seq: 0, agent: null });
  const [selected, setSelected] = useState(0);
  const [paused, setPaused] = useState(false);
  const live = officeState(data, job, connected);
  const realPaused = !connected || job?.status === 'parando' || live.label.startsWith('Aguardando');

  useEffect(() => {
    if (!job?.active && !preview) {
      setDeliveries([]);
      setTravel(0);
    }
  }, [job?.active, preview]);

  useEffect(() => {
    if (!connected) return;
    const next = officeTransitions(cursor.current, job, data.id);
    cursor.current = next.cursor;
    if (next.reset) { 
      setDeliveries([]); 
      setTravel(0); 
    } else if (next.deliveries.length) {
      setDeliveries(current => {
        const combined = [...current, ...next.deliveries];
        const deduplicated = [];
        for (const item of combined) {
          if (!deduplicated.length || deduplicated.at(-1).from !== item.from || deduplicated.at(-1).to !== item.to) {
            deduplicated.push(item);
          }
        }
        return deduplicated.slice(0, 1);
      });
    }
  }, [data.id, job, connected]);

  useEffect(() => {
    if (paused || (!preview && (!deliveries.length || realPaused || !job?.active))) return;
    let previous = performance.now();
    const timer = setInterval(() => { 
      const now = performance.now(); 
      const delta = Math.min(now - previous, 100); 
      previous = now; 
      setTravel(t => t + delta); 
    }, 40);
    return () => clearInterval(timer);
  }, [preview, paused, deliveries.length, realPaused, job?.active]);

  useEffect(() => {
    if (preview) {
      const currentStep = Math.floor(travel / DELIVERY_DURATION);
      if (currentStep >= 5) {
        setPreview(false);
        setStep(0);
        setTravel(0);
      } else {
        setStep(currentStep);
      }
    } else if (deliveries.length && travel >= DELIVERY_DURATION) {
      setDeliveries(current => current.slice(1));
      setTravel(0);
    }
  }, [travel, preview, deliveries.length]);

  useEffect(() => { 
    setPreview(false); 
    setStep(0); 
    setTravel(0); 
  }, [data.id, job?.id]);

  useEffect(() => { 
    if (job?.active) setPreview(false); 
  }, [job?.active]);

  const courier = preview ? step : deliveries[0]?.from;
  const recipient = preview ? (step + 1) % 5 : deliveries[0]?.to;
  const hasDelivery = Boolean(preview || (deliveries.length > 0 && job?.active));
  const active = preview ? step : live.index;
  const moving = !paused && (preview || (!realPaused && (hasDelivery || live.moving)));
  const agent = officeAgents[selected];
  const cycle = hasDelivery ? (travel % DELIVERY_DURATION) / DELIVERY_DURATION : 0;
  const away = hasDelivery && cycle >= 0.12 && cycle < 0.96;
  const delivering = cycle < 0.54;
  const walking = away && (cycle < 0.54 || cycle > 0.64);
  const route = deliveryRoute(courier ?? 0, recipient ?? 1);
  const position = alongRoute(route, delivering ? (cycle - 0.12) / 0.42 : cycle <= 0.64 ? 1 : 1 - (cycle - 0.64) / 0.32);
  return <section className="agent-office" aria-label="Escritório 2D dos agentes">
    <div className="office-heading"><div><span className="office-eyebrow">CENTRAL DE AGENTES</span><h2>Uma equipe, cada etapa à vista.</h2><p>Acompanhe os contratos da coleta à revisão.</p></div><div className="office-heading-actions"><div className="office-launch-buttons"><button className="office-start" disabled={!available} onClick={onStart} title={!connected ? 'Reconecte o executor para iniciar' : job?.active ? 'Aguarde o trabalho atual terminar' : 'Iniciar nova coleta, análise e arquivamento'}>{sending ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />} {sending ? 'Iniciando…' : 'Nova auditoria'}</button><button className="office-start office-resume" disabled={!available || !canResume} onClick={onResume} title={!canResume ? 'Selecione uma execução local com coleta salva e auditoria pendente' : !connected ? 'Reconecte o executor para retomar' : job?.active ? 'Aguarde o trabalho atual terminar' : 'Continuar a auditoria selecionada a partir dos lotes salvos'}><RefreshCw size={16} />Retomar auditoria</button></div><span className={`office-connection ${moving ? 'on' : ''}`}><i />{preview ? 'PRÉVIA ANIMADA · FICTÍCIA' : 'ESTADO DO EXECUTOR'}</span></div></div>
    {error && <p className="office-start-error" role="alert">{error}</p>}
    {preview && (
      <div style={{
        background: '#1d3444',
        border: '1px solid #456275',
        borderRadius: '8px',
        margin: '0 24px 14px',
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        color: '#d1e6f0',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <span>ℹ️ <strong>Modo Demonstração:</strong> Esta animação ilustra o fluxo dos agentes e parará automaticamente após um ciclo.</span>
        <button 
          className="office-button" 
          style={{ background: '#2f495b', color: '#fff', borderColor: '#628299' }} 
          onClick={() => { setPreview(false); setStep(0); setTravel(0); }}
        >
          Parar e voltar ao estado real
        </button>
      </div>
    )}
    {!preview && <CollectorSources data={data} job={job} connected={connected} />}
    {!preview && data.review?.status === 'em_andamento' && data.review?.total_lotes && (
      <div style={{
        background: '#152534',
        border: '1px solid #2d4558',
        borderRadius: '8px',
        margin: '0 24px 14px',
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        color: '#d6e7f2',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px' }}>🔍</span>
          <span>
            <strong>Revisão em dupla (Investigador &amp; Revisor):</strong> Processando lote {data.review.lote_atual || 1} de {data.review.total_lotes} ({data.review.total_contratos} contratos sob análise).
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '110px', height: '6px', background: '#253847', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{ width: `${Math.round(((data.review.lotes_concluidos || 0) / data.review.total_lotes) * 100)}%`, height: '100%', background: '#56bdc6', transition: 'width 0.3s ease' }} />
          </div>
          <span style={{ fontSize: '11px', color: '#9ec4d8', fontWeight: 'bold' }}>{Math.round(((data.review.lotes_concluidos || 0) / data.review.total_lotes) * 100)}%</span>
        </div>
      </div>
    )}
    <div className={`office-scene ${moving ? 'is-moving' : ''}`}>
      <svg viewBox="0 0 840 490" role="img" aria-label={`Escritório com cinco agentes. ${preview ? 'Demonstração fictícia' : live.label}`}>
        <defs><pattern id="office-floor" width="40" height="20" patternUnits="userSpaceOnUse"><rect width="40" height="20" fill="#334251" /><path d="M0 0h40v20H0Z" fill="none" stroke="#3b4b5a" strokeWidth="1" /></pattern></defs>
        <rect x="20" y="30" width="800" height="440" rx="12" fill="#111c29" />
        <rect x="36" y="62" width="768" height="390" fill="url(#office-floor)" />
        <path d="M36 62V38h768v24" fill="#647181" />
        <rect x="42" y="240" width="756" height="50" rx="5" fill="#253541" />
        <path d="M78 266H764" stroke="#788e98" strokeDasharray="4 10" opacity=".3" />
        {rooms.map((r,i) => { const doorY = r.top ? r.y+r.h : r.y; return <g key={i} className="office-private-room" aria-label={`Escritório do ${officeAgents[i].name}`}>
          <rect x={r.x} y={r.y} width={r.w} height={r.h} fill={officeAgents[i].color} opacity=".08" />
          <path d={`M${r.x} ${r.y}V${r.y+r.h}H${r.x+r.w}V${r.y}Z`} fill="none" stroke="#152330" strokeWidth="9" />
          <path d={`M${r.x} ${r.y}H${r.x+r.w}`} stroke="#72818a" strokeWidth="6" />
          <path d={`M${r.door-36} ${doorY}h72`} stroke="#334251" strokeWidth="12" />
          <path d={`M${r.door-36} ${doorY-5}v10m72-10v10`} stroke="#b6aa91" strokeWidth="4" />
          <path d={`M${r.door-34} ${doorY}l0 ${r.top ? -30 : 30}`} stroke="#b6aa91" strokeWidth="3" />
          <rect x={r.x+17} y={r.y+13} width="69" height="20" rx="3" fill="#182a38" stroke={officeAgents[i].color} strokeOpacity=".5" />
          <text x={r.x+51} y={r.y+27} textAnchor="middle" fill={officeAgents[i].color} fontSize="9" letterSpacing="1">SALA 0{i+1}</text>
          {r.top && <g transform={`translate(${r.x+r.w-90} ${r.y+15})`}><rect width="65" height="24" fill="#243745" stroke="#8ba1ac" strokeWidth="3" /><path d="M32 0v24" stroke="#8ba1ac" strokeWidth="3" /><path d="M6 8h20m13 0h20" stroke="#63adbd" strokeWidth="7" /></g>}
        </g>; })}
        <text x="67" y="340" fill="#a2b5c0" fontSize="10" letterSpacing="2" transform="rotate(-90 67 340)">AUDITORIA CIDADÃ</text>
        {desks.map(([x,y], i) => <g key={i}>
          <rect x={x-30} y={y+52} width="162" height={i < 3 ? 36 : 55} rx="6" fill={active === i ? officeAgents[i].color : '#4e6170'} opacity={active === i ? '.25' : '.12'} />
          <rect x={x-24} y={y+12} width="150" height="47" rx="4" fill="#182432" /><rect x={x-28} y={y} width="150" height="43" rx="4" fill="#a78060" stroke="#d1ac7e" strokeWidth="3" />
          <rect x={x+12} y={y-27} width="48" height="32" rx="3" fill="#172431" stroke="#8ca2ae" strokeWidth="3" />
          <rect x={x+18} y={y-21} width="36" height="19" fill={active === i ? '#0c1a24' : '#476674'} />
          {/* Mini-engrenagem girando na tela do computador do agente ativo */}
          {active === i && (
            <g transform={`translate(${x+36} ${y-11.5})`}>
              <GearIcon color={officeAgents[i].color} clockwise={true} size={0.52} speed="2s" />
            </g>
          )}
          <path d={`M${x+22} ${y+13}h30`} stroke="#d0c7b3" strokeWidth="5" />
          <rect x={x+82} y={y+6} width="17" height="23" fill="#eee5d2" /><path d={`M${x+85} ${y+12}h10m-10 5h10m-10 5h7`} stroke="#8c9aa2" strokeWidth="2" />
          {!(away && i === courier) && <Person x={x+36} y={y+51} color={officeAgents[i].color} working={active === i} carrying={hasDelivery && i === recipient && cycle >= .54} />}
          <text x={x+45} y={y+ (i<3 ? 86 : 101)} textAnchor="middle" fill={active === i ? '#fff' : '#afc0ca'} fontSize="14" fontWeight="600">{officeAgents[i].name}</text>
          {active === i && (
            <g className="office-work-badge" transform={`translate(${x+45} ${y + (i < 3 ? 104 : 119)})`}>
              <rect x="-44" y="-8.5" width="88" height="17" rx="8.5" fill="#112231" stroke={officeAgents[i].color} strokeWidth="1.2" />
              <g transform="translate(-32 0)">
                <GearIcon color={officeAgents[i].color} clockwise={true} size={0.38} speed="2s" />
              </g>
              <text x="-21" y="3.2" fill="#e2edf3" fontSize="7.8" fontWeight="700" letterSpacing="0.8">TRABALHANDO</text>
              <circle cx="34" cy="0" r="2.2" fill="#4ade80">
                <animate attributeName="opacity" values="0.2;1;0.2" dur="1.2s" repeatCount="indefinite" />
              </circle>
            </g>
          )}
        </g>)}
        {[ [755,180], [750,390] ].map(([x,y]) => <g key={x+':'+y} transform={`translate(${x} ${y})`}><rect x="-9" width="18" height="19" rx="3" fill="#ac8265" /><path d="M0 0v-37M0-10l-13-17M0-15l13-19" stroke="#80b49b" strokeWidth="8" /></g>)}
        {away && <g className="office-walker" data-delivery-agent={officeAgents[courier].name} data-delivery-to={officeAgents[recipient].name} data-delivery-source={preview ? 'preview' : 'executor'} data-delivery-phase={delivering ? 'levando' : cycle <= .64 ? 'entregando' : 'voltando'}><Person x={position[0]} y={position[1]} color={officeAgents[courier].color} walking={walking} carrying={delivering} working={true} /></g>}
      </svg>
      <div className="office-scene-caption"><span className={moving ? 'office-pulse' : ''} />{preview ? `Prévia: ${officeAgents[step].name} ${paused ? '· pausada' : 'entregando documentos'}` : live.label}</div>
      {!preview && hasDelivery && (
        <div className="office-scene-caption">
          {data.review?.status === 'em_andamento' && [3, 4].includes(courier) && [3, 4].includes(recipient)
            ? `Revisão conjunta: ${officeAgents[courier].name} encaminhando lote ${data.review.lote_atual || 1} de ${data.review.total_lotes} para ${officeAgents[recipient].name}`
            : `Entrega visual: ${officeAgents[courier].name} → ${officeAgents[recipient].name} · troca de etapa registrada${(paused || realPaused) ? ' · pausada' : ''}${deliveries.length > 1 ? ` · ${deliveries.length-1} na fila` : ''}`}
        </div>
      )}
    </div>
    <div className="office-toolbar"><p>{preview ? 'Fluxo ilustrativo. Nenhuma auditoria está sendo executada pela prévia.' : 'As estações respondem ao estado informado pelo executor. Fontes e ferramentas aparecem no acompanhamento abaixo.'}</p><div><button className="office-button" onClick={() => setPaused(p => !p)}>{paused ? 'Retomar animação' : 'Pausar animação'}</button><button className="office-button accent" aria-pressed={preview} disabled={Boolean(job?.active)} onClick={() => { setPreview(p => !p); setStep(0); setTravel(0); setPaused(false); }}>{preview ? 'Voltar ao estado real' : 'Ver prévia do fluxo'}</button></div></div>
    <div className="office-agent-tabs" role="group" aria-label="Conhecer os agentes">{officeAgents.map((a,i) => <button key={a.name} className={selected === i ? 'selected' : ''} aria-pressed={selected === i} onClick={() => setSelected(i)}><i style={{ background: a.color }} />{a.name}{active === i && <small>{preview ? 'prévia' : 'ativo'}</small>}</button>)}</div>
    <div className="office-agent-detail"><strong style={{ color: agent.color }}>{agent.name}</strong><span>{agent.task}.</span><small>{preview ? 'Demonstração visual' : active === selected ? moving ? 'Etapa em andamento' : 'Etapa aguardando' : 'Sem atividade confirmada nesta estação'}</small></div>
  </section>;
}
