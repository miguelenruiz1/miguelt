import { useState, useMemo } from 'react'

const COLOR = '#00d4ff'
const BG = '#080c14'

const SHAPES = {
  pentagon: {
    sides: 5, radius: 130, label: '5 NODOS · EUDR CHAIN',
    nodeLabels: ['ORIGEN', 'ADUANA', 'PUERTO', 'TRÁNSITO', 'DESTINO'],
  },
  hexagon: {
    sides: 6, radius: 125, label: '6 NODOS · SUPPLY CHAIN',
    nodeLabels: ['COSECHA', 'PROCESO', 'INSPEC.', 'ADUANA', 'PUERTO', 'DESTINO'],
  },
  triangle: {
    sides: 3, radius: 130, label: '3 NODOS · FAST TRACK',
    nodeLabels: ['ORIGEN', 'CONTROL', 'DESTINO'],
  },
  square: {
    sides: 4, radius: 120, label: '4 NODOS · STANDARD',
    nodeLabels: ['GRANJA', 'PLANTA', 'ADUANA', 'DESTINO'],
  },
} as const

type ShapeName = keyof typeof SHAPES
interface Pt { x: number; y: number }

function getPoints(sides: number, radius: number): Pt[] {
  return Array.from({ length: sides }, (_, i) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / sides
    return { x: radius * Math.cos(a), y: radius * Math.sin(a) }
  })
}

function ptsStr(pts: Pt[]) {
  return pts.map(p => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
}

function buildPath(pts: Pt[]) {
  return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ') + ' Z'
}

function perim(pts: Pt[]) {
  let t = 0
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length]
    t += Math.hypot(b.x - a.x, b.y - a.y)
  }
  return t
}

const CSS = `
.tl-base{fill:none;stroke:${COLOR}22;stroke-width:1.5}
.tl-glow-s{fill:none;stroke:${COLOR}18;stroke-width:2}
.tl-trace{
  fill:none;stroke:url(#tl-traceGrad);stroke-width:3;stroke-linecap:round;
  filter:url(#tl-glow);animation:tl-trace 3.2s cubic-bezier(.4,0,.2,1) infinite;
}
.tl-dot{
  fill:#fff;filter:url(#tl-dotGlow);
  animation:tl-dot 3.2s cubic-bezier(.4,0,.2,1) infinite;
}
.tl-node{fill:#0a2a3a;stroke:${COLOR};stroke-width:1.5;animation:tl-nPulse 3.2s ease-in-out infinite}
.tl-ni{fill:${COLOR};animation:tl-niPulse 3.2s ease-in-out infinite}
.tl-lbl{fill:${COLOR};font-size:8px;font-family:'Courier New',monospace;letter-spacing:1px;opacity:.6}
.tl-spoke{stroke:${COLOR}15;stroke-width:.5;stroke-dasharray:3 4}
.tl-center{animation:tl-cPulse 2s ease-in-out infinite alternate;transform-origin:0 0}
.tl-status{fill:${COLOR};font-size:8px;font-family:'Courier New',monospace;letter-spacing:3px;opacity:0;animation:tl-sFade 3.2s ease-in-out infinite}
.tl-particle{fill:${COLOR};animation:tl-pDrift linear infinite;opacity:0}
.tl-btn{
  background:transparent;border:1px solid ${COLOR}33;color:${COLOR};
  padding:8px 20px;font-size:9px;letter-spacing:3px;text-transform:uppercase;
  font-family:'Courier New',monospace;cursor:pointer;transition:all .2s;border-radius:2px;
}
.tl-btn:hover{background:${COLOR}11;border-color:${COLOR};box-shadow:0 0 12px ${COLOR}44}
.tl-btn.active{background:${COLOR}22;border-color:${COLOR}}

@keyframes tl-trace{
  0%{stroke-dashoffset:1000;opacity:1}
  85%{stroke-dashoffset:0;opacity:1}
  95%{stroke-dashoffset:0;opacity:.8}
  100%{stroke-dashoffset:1000;opacity:0}
}
@keyframes tl-dot{
  0%{offset-distance:0%;opacity:1}
  85%{offset-distance:100%;opacity:1}
  86%{offset-distance:100%;opacity:0}
  100%{offset-distance:0%;opacity:0}
}
@keyframes tl-nPulse{0%,100%{opacity:.4}50%{opacity:1}}
@keyframes tl-niPulse{0%,100%{opacity:.2}50%{opacity:1}}
@keyframes tl-cPulse{from{opacity:.3;transform:scale(.9)}to{opacity:.9;transform:scale(1.1)}}
@keyframes tl-sFade{0%{opacity:0}60%{opacity:0}80%{opacity:.7}95%{opacity:.7}100%{opacity:0}}
@keyframes tl-pDrift{
  0%{opacity:0;transform:translate(0,0) scale(1)}
  20%{opacity:.6}80%{opacity:.3}
  100%{opacity:0;transform:translate(var(--tl-dx),var(--tl-dy)) scale(.3)}
}
`

const PARTICLES = Array.from({ length: 8 }, (_, i) => {
  const a = i * 2.399 + 0.5
  const r = 60 + ((i * 37) % 80)
  return {
    cx: +(r * Math.cos(a)).toFixed(1),
    cy: +(r * Math.sin(a)).toFixed(1),
    r: +(1 + (i % 3) * 0.5).toFixed(1),
    dx: `${((i * 17) % 40) - 20}px`,
    dy: `${((i * 23) % 40) - 20}px`,
    dur: `${3 + (i % 4)}s`,
    delay: `${i * 0.4}s`,
  }
})

const BUTTONS: { key: ShapeName; label: string }[] = [
  { key: 'pentagon', label: 'Pentágono' },
  { key: 'hexagon', label: 'Hexágono' },
  { key: 'triangle', label: 'Triángulo' },
  { key: 'square', label: 'Cuadrado' },
]

export function BlockchainAnimation() {
  const [shape, setShape] = useState<ShapeName>('pentagon')
  const config = SHAPES[shape]

  const geo = useMemo(() => {
    const pts = getPoints(config.sides, config.radius)
    return { pts, str: ptsStr(pts), path: buildPath(pts), perim: perim(pts) }
  }, [config.sides, config.radius])

  return (
    <div
      className="absolute inset-0 flex flex-col items-center justify-center overflow-hidden"
      style={{ background: BG, fontFamily: "'Courier New', monospace" }}
    >
      <style>{CSS}</style>

      {/* Title */}
      <h1
        style={{
          color: COLOR,
          fontSize: 11,
          letterSpacing: 6,
          textTransform: 'uppercase' as const,
          opacity: 0.5,
          marginBottom: 32,
        }}
      >
        TraceLog — Trazabilidad & Inventario
      </h1>

      {/* Stage — remount on shape change to restart animations */}
      <div key={shape} style={{ position: 'relative', width: 380, height: 380 }}>
        <svg viewBox="-180 -180 360 360" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
          <defs>
            <filter id="tl-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="b1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="b2" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="16" result="b3" />
              <feMerge>
                <feMergeNode in="b3" /><feMergeNode in="b2" />
                <feMergeNode in="b1" /><feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="tl-dotGlow" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="b1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="12" result="b2" />
              <feMerge>
                <feMergeNode in="b2" /><feMergeNode in="b1" /><feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <linearGradient id="tl-traceGrad" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor={COLOR} stopOpacity={0} />
              <stop offset="60%" stopColor={COLOR} stopOpacity={0.8} />
              <stop offset="100%" stopColor="#ffffff" stopOpacity={1} />
            </linearGradient>
          </defs>

          {/* Ambient particles */}
          {PARTICLES.map((p, i) => (
            <circle
              key={i}
              cx={p.cx}
              cy={p.cy}
              r={p.r}
              className="tl-particle"
              style={{ '--tl-dx': p.dx, '--tl-dy': p.dy, animationDuration: p.dur, animationDelay: p.delay } as React.CSSProperties}
            />
          ))}

          {/* Spokes to center */}
          {geo.pts.map((p, i) => (
            <line key={i} x1={0} y1={0} x2={p.x} y2={p.y} className="tl-spoke" />
          ))}

          {/* Base polygon */}
          <polygon points={geo.str} className="tl-base" />
          <polygon points={geo.str} className="tl-glow-s" />

          {/* Animated trace line */}
          <polygon
            points={geo.str}
            className="tl-trace"
            style={{ strokeDasharray: geo.perim + 10, strokeDashoffset: geo.perim + 10 }}
          />

          {/* Leading light dot */}
          <circle
            r="4"
            className="tl-dot"
            style={{ offsetPath: `path('${geo.path}')` } as React.CSSProperties}
          />

          {/* Vertex nodes + labels */}
          {geo.pts.map((p, i) => {
            const la = Math.atan2(p.y, p.x)
            const lr = config.radius + 22
            return (
              <g key={i}>
                <circle cx={p.x} cy={p.y} r={7} className="tl-node" style={{ animationDelay: `${i * 0.2}s` }} />
                <circle cx={p.x} cy={p.y} r={2.5} className="tl-ni" style={{ animationDelay: `${i * 0.2}s` }} />
                <text x={lr * Math.cos(la)} y={lr * Math.sin(la) + 3} textAnchor="middle" className="tl-lbl">
                  {config.nodeLabels[i]}
                </text>
              </g>
            )
          })}

          {/* Center logo */}
          <g className="tl-center">
            <circle cx={0} cy={0} r={22} fill="none" stroke={COLOR} strokeWidth={1} opacity={0.3} />
            <circle cx={0} cy={0} r={14} fill="#050d1a" stroke={`${COLOR}22`} strokeWidth={1} />
            <polygon
              points="0,-9 7.8,-4.5 7.8,4.5 0,9 -7.8,4.5 -7.8,-4.5"
              fill="none" stroke={COLOR} strokeWidth={1.2} opacity={0.8}
            />
            <circle cx={0} cy={0} r={3} fill={COLOR} opacity={0.9} />
            <text x={0} y={3} textAnchor="middle" fill={COLOR} fontSize={6} fontFamily="Courier New" letterSpacing={1} opacity={0.9}>
              TL
            </text>
          </g>

          {/* Status text */}
          <text className="tl-status" x={0} y={155} textAnchor="middle">VERIFIED</text>
        </svg>
      </div>

      {/* Shape controls */}
      <div className="flex gap-3 mt-8 flex-wrap justify-center px-4">
        {BUTTONS.map(b => (
          <button
            key={b.key}
            onClick={() => setShape(b.key)}
            className={`tl-btn ${shape === b.key ? 'active' : ''}`}
          >
            {b.label}
          </button>
        ))}
      </div>

      {/* Shape label */}
      <span style={{ color: COLOR, fontSize: 9, letterSpacing: 4, textTransform: 'uppercase' as const, opacity: 0.3, marginTop: 16 }}>
        {config.label}
      </span>
    </div>
  )
}
