import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import './landing.css'

export function LandingPage() {
  const [faqOpen, setFaqOpen] = useState<number | null>(null)
  const [cd, setCd] = useState({ days: 0, hours: 0, mins: 0 })

  useEffect(() => {
    const update = () => {
      const diff = new Date('2026-12-30T00:00:00').getTime() - Date.now()
      if (diff <= 0) return
      setCd({ days: Math.floor(diff / 86400000), hours: Math.floor((diff % 86400000) / 3600000), mins: Math.floor((diff % 3600000) / 60000) })
    }
    update()
    const id = setInterval(update, 60000)
    return () => clearInterval(id)
  }, [])

  // Scroll-reveal
  const observerRef = useRef<IntersectionObserver | null>(null)
  useEffect(() => {
    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { (e.target as HTMLElement).style.opacity = '1'; (e.target as HTMLElement).style.transform = 'translateY(0)' } })
    }, { threshold: 0.1 })
    document.querySelectorAll('.lp .quien-card,.lp .modulo-card,.lp .dolor-item,.lp .solucion-item,.lp .precio-card').forEach(el => {
      (el as HTMLElement).style.opacity = '0';
      (el as HTMLElement).style.transform = 'translateY(20px)';
      (el as HTMLElement).style.transition = 'opacity 0.5s ease, transform 0.5s ease, border-color 0.3s';
      observerRef.current?.observe(el)
    })
    return () => observerRef.current?.disconnect()
  }, [])

  const scrollTo = (id: string) => (e: React.MouseEvent) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }) }

  const faqs = [
    { q: '¿Cuánto tiempo tarda implementar TraceLog?', a: 'Menos de 30 minutos. Creas tu cuenta, subes tus productos y ya estás operando. No necesitas consultores ni capacitación previa.' },
    { q: '¿Necesito saber de blockchain para usar el módulo de logística?', a: 'Para nada. El blockchain es completamente transparente — tú registras los eventos normalmente y el sistema ancla todo en Solana automáticamente. Solo ves el resultado: un certificado verificable con QR.' },
    { q: '¿Funciona con mi sistema contable actual (Siigo, World Office)?', a: 'Sí. TraceLog tiene webhooks que envían eventos a sistemas externos. Puedes sincronizar facturas y movimientos automáticamente con tu software contable.' },
    { q: '¿Qué pasa si la norma EUDR cambia o se actualiza?', a: 'Las actualizaciones normativas están incluidas en tu suscripción sin costo adicional. Cuando la UE actualice la norma, nosotros actualizamos el sistema.' },
    { q: '¿Están seguros mis datos?', a: 'Sí. TraceLog corre en Google Cloud Platform (São Paulo), con backups diarios, HTTPS automático, encriptación y aislamiento total por empresa.' },
    { q: '¿Puedo cancelar cuando quiera?', a: 'Sí, sin penalizaciones ni contratos de permanencia. Cancela cualquier módulo o tu cuenta completa en cualquier momento.' },
  ]

  return (
    <div className="lp">

      {/* NAV */}
      <nav>
        <Link to="/home" className="nav-logo"><span className="nav-logo-dot" />Trace<span>Log</span></Link>
        <ul className="nav-links">
          <li><a href="#modulos" onClick={scrollTo('modulos')}>Módulos</a></li>
          <li><a href="#precios" onClick={scrollTo('precios')}>Precios</a></li>
          <li><a href="#como" onClick={scrollTo('como')}>Cómo funciona</a></li>
          <li><a href="#faq" onClick={scrollTo('faq')}>FAQ</a></li>
        </ul>
        <div className="nav-ctas">
          <Link to="/login" className="btn-ghost">Iniciar sesión</Link>
          <Link to="/register" className="btn-primary">Comenzar →</Link>
        </div>
      </nav>

      {/* URGENCY BANNER */}
      <div className="urgency-banner">
        <span className="urgency-dot" />
        <span>⚠ La norma EUDR entra en vigor en <strong>diciembre 2026</strong> — exportadores a Europa deben cumplirla o pierden acceso al mercado</span>
        <a href="#eudr" onClick={scrollTo('eudr')} style={{ color: 'var(--amber)', fontWeight: 600, fontSize: 13, textDecoration: 'none', whiteSpace: 'nowrap' }}>Saber más →</a>
      </div>

      {/* HERO */}
      <section className="hero">
        <div>
          <div className="hero-tag"><span className="nav-logo-dot" />Plataforma SaaS modular</div>
          <h1>Tu operación<br />bajo <em>control total</em>,<br />desde el primer día</h1>
          <p className="hero-sub">Inventario, producción, logística con blockchain, cumplimiento EUDR e inteligencia artificial. Activa solo lo que necesitas. Sin contratos. Sin sorpresas.</p>
          <div className="hero-ctas">
            <Link to="/register" className="btn-primary btn-lg">Crear cuenta →</Link>
            <a href="#como" onClick={scrollTo('como')} className="btn-ghost btn-lg">Ver cómo funciona</a>
          </div>
          <div className="hero-stats">
            <div className="stat"><span className="stat-num">6</span><span className="stat-label">Módulos activables</span></div>
            <div className="stat"><span className="stat-num">30s</span><span className="stat-label">Para empezar</span></div>
            <div className="stat"><span className="stat-num">GCP</span><span className="stat-label">Infraestructura</span></div>
          </div>
        </div>
        <div className="hero-visual">
          <div className="mockup-shell">
            <div className="mockup-bar">
              <div className="mockup-dot" style={{ background: '#FF5F57' }} />
              <div className="mockup-dot" style={{ background: '#FFBD2E' }} />
              <div className="mockup-dot" style={{ background: '#28C840' }} />
              <div style={{ flex: 1, background: 'rgba(255,255,255,0.05)', borderRadius: 4, height: 16, marginLeft: 8 }} />
            </div>
            <div className="mockup-body">
              <div className="mockup-header"><span className="mockup-title">Dashboard — Cooperativa Las Palmas</span><span className="mockup-badge">● En línea</span></div>
              <div className="mockup-cards">
                <div className="mockup-card"><div className="mockup-card-label">Stock valorizado</div><div className="mockup-card-value">$847M</div><div className="mockup-card-sub">↑ 12% este mes</div></div>
                <div className="mockup-card"><div className="mockup-card-label">Órdenes activas</div><div className="mockup-card-value">34</div><div className="mockup-card-sub">↑ 8 nuevas hoy</div></div>
                <div className="mockup-card"><div className="mockup-card-label">Certificados EUDR</div><div className="mockup-card-value">127</div><div className="mockup-card-sub">↑ Verificables</div></div>
              </div>
              <div className="mockup-chart"><div className="mockup-chart-label">Movimientos de inventario — últimos 7 días</div><div className="chart-bars">{[40,65,50,80,95,70,60].map((h,i) => <div key={i} className={`chart-bar${i===4?' active':''}`} style={{ height: `${h}%` }} />)}</div></div>
              <div className="mockup-row">
                <div className="mockup-eudr"><div className="mockup-eudr-title">Cumplimiento EUDR</div>{['Parcelas verificadas GFW','DDS enviada a TRACES NT','Certificado en Solana','Riesgo: CERO'].map(t => <div key={t} className="mockup-eudr-item"><div className="eudr-check">✓</div>{t}</div>)}</div>
                <div className="mockup-blockchain"><div className="chain-title">Blockchain</div>{['0x4f2a...','0x8b1c...','0x2e9f...'].map(h => <div key={h} className="chain-item"><div className="chain-dot" /><div className="chain-line">{h}</div></div>)}<div style={{ fontSize: 9, color: 'var(--green)', marginTop: 6 }}>Solana ● Verificado</div></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* LOGOS */}
      <div style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="logos-section">
          <div className="logos-label">Integrado con las plataformas que el mundo usa</div>
          <div className="logos-grid">
            {[
              { icon: '🌍', bg: 'rgba(0,232,122,0.1)', color: 'var(--green)', name: 'Global Forest Watch' },
              { icon: '⬡', bg: 'rgba(99,102,241,0.1)', color: '#818cf8', name: 'Solana Blockchain' },
              { icon: '🇪🇺', bg: 'rgba(59,130,246,0.1)', color: '#60a5fa', name: 'TRACES NT (EU)' },
              { icon: '🏦', bg: 'rgba(245,158,11,0.1)', color: 'var(--amber)', name: 'DIAN Colombia' },
              { icon: '🤖', bg: 'rgba(16,185,129,0.1)', color: '#34d399', name: 'Anthropic Claude' },
              { icon: '☁', bg: 'rgba(239,68,68,0.1)', color: '#f87171', name: 'Google Cloud' },
            ].map(l => <div key={l.name} className="logo-item"><div className="logo-icon" style={{ background: l.bg, color: l.color }}>{l.icon}</div>{l.name}</div>)}
          </div>
        </div>
      </div>

      {/* QUIEN */}
      <section className="quien-section" id="quien">
        <div className="section-tag">Para quién</div>
        <h2 className="section-title">Una plataforma que crece<br />contigo</h2>
        <p className="section-sub">Empieza con lo que necesitas hoy. Activa más cuando tu negocio lo pida. Sin migraciones, sin perder datos.</p>
        <div className="quien-grid">
          {[
            { icon: '🏪', name: 'Tiendas y comercios', desc: 'Controla tu stock, maneja compras y ventas, y olvídate del Excel para siempre.', mods: [['Inventario',true],['Facturación DIAN',true],['Producción',false],['Logística',false]] },
            { icon: '🏭', name: 'Fabricantes y procesadores', desc: 'Recetas, corridas de producción, MRP, costeo real. Todo conectado con tu inventario.', mods: [['Inventario',true],['Producción',true],['Facturación DIAN',true],['Logística',false]] },
            { icon: '🚚', name: 'Distribuidores y traders', desc: 'Trazabilidad de cada carga, cadena de custodia verificable, documentos de transporte.', mods: [['Inventario',true],['Logística',true],['IA',true],['EUDR',false]] },
            { icon: '✈️', name: 'Exportadores a Europa', desc: 'Cumple EUDR, genera certificados verificables en blockchain, conecta directo con TRACES NT.', mods: [['Todo incluido',true],['EUDR',true],['Blockchain',true]], highlight: true },
          ].map(c => (
            <div key={c.name} className="quien-card" style={c.highlight ? { borderColor: 'var(--border2)', background: 'linear-gradient(135deg,rgba(0,232,122,0.05),var(--bg2))' } : undefined}>
              <div className="quien-icon">{c.icon}</div>
              <div className="quien-name">{c.name}</div>
              <div className="quien-desc">{c.desc}</div>
              <div className="quien-modulos">{c.mods.map(([m, a]) => <span key={m as string} className={`modulo-pill${a ? ' active' : ''}`}>{m as string}</span>)}</div>
            </div>
          ))}
        </div>
      </section>

      {/* DOLOR */}
      <section className="dolor-section">
        <div className="dolor-inner">
          <div className="section-tag">El problema</div>
          <h2 className="section-title">Tus herramientas actuales<br />te están costando plata</h2>
          <div className="dolor-grid">
            <div className="dolor-items">
              {[
                { t: 'Excel no es un sistema de inventario', d: 'Cuando llega una orden grande no sabes exactamente cuánto tienes, dónde está, ni cuánto vale. Los errores se acumulan y el margen desaparece.' },
                { t: 'Produces más de lo que crees', d: 'Sin costeo real por producción no sabes si tu producto más vendido te da plata o te la quita. Los desperdicios no aparecen en ningún lado.' },
                { t: 'EUDR te puede cerrar Europa', d: 'Sin trazabilidad de parcelas y sin declaración DDS, un inspector europeo puede rechazar tu embarque. Eso son millones de pesos perdidos.' },
              ].map(p => <div key={p.t} className="dolor-item"><div className="dolor-x">✗</div><div className="dolor-text"><h4>{p.t}</h4><p>{p.d}</p></div></div>)}
            </div>
            <div className="solucion-items">
              {[
                { t: 'Stock en tiempo real, siempre exacto', d: 'FIFO, FEFO, LIFO, promedio ponderado. Kardex valorizado. Alertas automáticas. Sabes exactamente qué tienes y cuánto vale en cada momento.' },
                { t: 'Costeo real de cada corrida', d: 'BOM con versiones, emisión automática de materiales, varianza real vs estándar. Sabes exactamente cuánto te cuesta producir cada unidad.' },
                { t: 'Certificado EUDR en 3 minutos', d: 'Parcela verificada vs GFW, DDS enviada a TRACES NT, certificado PDF con QR anclado en Solana. Lo que una consultora hace en semanas, TraceLog lo hace en minutos.' },
              ].map(s => <div key={s.t} className="solucion-item"><div className="solucion-check">✓</div><div className="solucion-text"><h4>{s.t}</h4><p>{s.d}</p></div></div>)}
            </div>
          </div>
        </div>
      </section>

      {/* MODULOS */}
      <section className="modulos-section" id="modulos">
        <div className="section-tag">Módulos</div>
        <h2 className="section-title">Activa solo lo que necesitas</h2>
        <p className="section-sub">Cada módulo funciona solo y se conecta con los demás. Empieza con inventario y agrega producción cuando crezcas.</p>
        <div className="modulos-grid">
          {[
            { num: '01', icon: '📦', title: 'Inventario', sub: 'Control total de productos, stock, compras y ventas. Multi-bodega, valorización FIFO/FEFO/LIFO, kardex y reportes.', feats: ['Multi-bodega con ubicaciones','Valorización FIFO / FEFO / LIFO','Compras, ventas y devoluciones','Alertas de stock y auto-reorden'], iconBg: 'rgba(0,232,122,0.08)', iconBorder: 'var(--border2)' },
            { num: '02', icon: '⚙️', title: 'Producción', sub: 'Recetas BOM con versiones, corridas de producción, MRP, costeo real y varianzas. Para fabricantes y procesadores.', feats: ['BOM recursivo con sub-ensambles','MRP con explosión automática','Costeo real vs estándar','Recursos y capacidad'], iconBg: 'rgba(99,102,241,0.08)', iconBorder: 'rgba(99,102,241,0.2)' },
            { num: '03', icon: '⛓️', title: 'Logística + Blockchain', sub: 'Cadena de custodia verificable. Cada movimiento queda registrado en Solana. Trazabilidad inmutable de punta a punta.', feats: ['Cadena de custodia inmutable','Anclaje en Solana blockchain','Verificación pública sin login','Documentos de transporte'], iconBg: 'rgba(59,130,246,0.08)', iconBorder: 'rgba(59,130,246,0.2)' },
            { num: '04', icon: '🌿', title: 'Cumplimiento EUDR', sub: 'El único en Latam con EUDR nativo. Parcelas verificadas vs GFW, DDS directo a TRACES NT, certificados PDF+QR+Solana.', feats: ['Parcelas con verificación GFW','Conexión directa TRACES NT (EU)','Certificados blockchain verificables','USDA Organic y FSSAI incluidos'], featured: true, iconBg: 'rgba(0,232,122,0.1)', iconBorder: 'var(--border2)' },
            { num: '05', icon: '🧾', title: 'Facturación DIAN', sub: 'Facturas electrónicas, notas crédito y débito ante la DIAN. Resoluciones, numeración automática y PDF.', feats: ['Emisión ante la DIAN en tiempo real','Notas crédito y débito','Gestión de resoluciones','PDF automático por factura'], iconBg: 'rgba(245,166,35,0.08)', iconBorder: 'rgba(245,166,35,0.2)' },
            { num: '06', icon: '🤖', title: 'Inteligencia Artificial', sub: 'Análisis de rentabilidad con Claude AI. Detecta márgenes negativos, sugiere acciones y aprende de tu operación.', feats: ['Margen real por producto','Alertas de margen automáticas','Recomendaciones accionables','Powered by Claude (Anthropic)'], iconBg: 'rgba(168,85,247,0.08)', iconBorder: 'rgba(168,85,247,0.2)' },
          ].map(m => (
            <div key={m.num} className={`modulo-card${m.featured ? ' featured' : ''}`}>
              <div className="modulo-num">Módulo {m.num}</div>
              <div className="modulo-icon-wrap" style={{ background: m.iconBg, borderColor: m.iconBorder }}>{m.icon}</div>
              <div className="modulo-card-title">{m.title}</div>
              <div className="modulo-card-sub">{m.sub}</div>
              <div className="modulo-features">{m.feats.map(f => <div key={f} className="feat-item"><div className="feat-dot" />{f}</div>)}</div>
            </div>
          ))}
        </div>
      </section>

      {/* COMO FUNCIONA */}
      <section className="como-section" id="como">
        <div className="como-inner">
          <div className="section-tag">Cómo funciona</div>
          <h2 className="section-title">Operando en minutos,<br />no en meses</h2>
          <p className="section-sub">Sin implementaciones, sin consultores, sin pagos adelantados. Tú registras y empiezas a operar el mismo día.</p>
          <div className="como-steps">
            {[
              { n: '1', t: 'Crea tu cuenta', d: 'Regístrate en 30 segundos. Te preguntamos a qué se dedica tu empresa y te recomendamos los módulos ideales.' },
              { n: '2', t: 'Configura tu operación', d: 'Sube tus productos, bodegas y proveedores. En menos de una hora ya tienes datos reales en el sistema.' },
              { n: '3', t: 'Opera y crece', d: 'Gestiona inventario, produce, despacha y exporta. Activa módulos cuando los necesites. Sin migraciones.' },
            ].map(s => <div key={s.n} className="como-step"><div className="step-circle">{s.n}</div><h3>{s.t}</h3><p>{s.d}</p></div>)}
          </div>
        </div>
      </section>

      {/* PRECIOS */}
      <section className="precios-section" id="precios">
        <div className="precios-inner">
          <div className="section-tag">Precios</div>
          <h2 className="section-title">Paga solo por lo que usas</h2>
          <p className="section-sub">Sin contratos de permanencia. Cancela cuando quieras. 20% de descuento pagando anual.</p>
          <div className="precios-grid">
            {[
              { name: 'Logística', para: 'Operadores logísticos y distribuidores', cop: '$490k', usd: '≈ $136 USD · ~$5.9M COP/año', items: ['Logística con blockchain','Cadena de custodia verificable','Tracking en tiempo real','Hasta 5 usuarios','Soporte por email'], cta: 'Comenzar →' },
              { name: 'Starter', para: 'Negocios que necesitan controlar su inventario', cop: '$490k', usd: '≈ $136 USD · ~$5.9M COP/año', items: ['Inventario completo','Facturación DIAN','Compras y ventas','Hasta 5 usuarios','Soporte por email'], cta: 'Comenzar →' },
              { name: 'Business', para: 'Productores y PyMEs en crecimiento', cop: '$990k', usd: '≈ $275 USD · ~$11.9M COP/año', items: ['Inventario + Logística','Producción + BOM + MRP','IA con Claude','Facturación DIAN','Hasta 15 usuarios'], cta: 'Comenzar →' },
              { name: 'Export Pro', para: 'Exportadores que venden a Europa', cop: '$3.9M', usd: '≈ $1.083 USD · ~$46.8M COP/año', items: ['Todo de Business','Cumplimiento EUDR completo','TRACES NT + GFW integrado','Certificados blockchain','Usuarios ilimitados'], cta: 'Comenzar →', popular: true },
              { name: 'Enterprise', para: 'Cooperativas y traders grandes', cop: '$7.9M+', usd: '≈ $2.194+ USD · precio a medida', items: ['Todo de Export Pro','Multi-empresa','API abierta + webhooks','Onboarding dedicado','SLA 99.9% garantizado'], cta: 'Contactar →', outline: true },
            ].map(p => (
              <div key={p.name} className={`precio-card${p.popular ? ' popular' : ''}`}>
                {p.popular && <div className="popular-badge">Más popular</div>}
                <div className="plan-name">{p.name}</div>
                <div className="plan-para">{p.para}</div>
                <div className="plan-price"><span className="plan-cop">{p.cop}</span><span className="plan-mes"> COP/mes</span></div>
                <div className="plan-usd">{p.usd}</div>
                <div className="plan-divider" />
                <div className="plan-features">{p.items.map(i => <div key={i} className="pf-item"><span className="pf-check">✓</span>{i}</div>)}</div>
                <Link to="/register" className={`plan-cta${p.popular ? ' cta-primary' : p.outline ? ' cta-outline' : ''}`}>{p.cta}</Link>
              </div>
            ))}
          </div>
          <div className="precios-note">¿Exportas $500k USD/año? TraceLog Export Pro cuesta el <strong>0.94% de tus ingresos</strong> anuales. Un embarque rechazado en Europa vale 10x más que tu suscripción anual.</div>
        </div>
      </section>

      {/* EUDR URGENCIA */}
      <section className="eudr-section" id="eudr">
        <div className="eudr-inner">
          <div className="section-tag" style={{ justifyContent: 'center' }}>Urgencia EUDR</div>
          <h2 className="section-title">El reloj corre.<br />¿Tu empresa está lista?</h2>
          <p style={{ color: 'var(--muted)', marginTop: 12 }}>La norma EUDR entra en vigor en diciembre 2026. Sin cumplimiento, tus exportaciones a Europa se bloquean.</p>
          <div className="eudr-countdown">
            <div className="countdown-unit"><div className="countdown-num">{cd.days}</div><div className="countdown-label">Días</div></div>
            <div className="countdown-sep">:</div>
            <div className="countdown-unit"><div className="countdown-num">{String(cd.hours).padStart(2, '0')}</div><div className="countdown-label">Horas</div></div>
            <div className="countdown-sep">:</div>
            <div className="countdown-unit"><div className="countdown-num">{String(cd.mins).padStart(2, '0')}</div><div className="countdown-label">Minutos</div></div>
          </div>
          <div className="eudr-warning">⚠ Las multas por incumplimiento EUDR pueden llegar al <strong>4% de tus ingresos anuales</strong> más la confiscación del producto y el cierre del acceso al mercado europeo.</div>
          <Link to="/register" className="btn-primary btn-lg">Prepara tu empresa ahora →</Link>
        </div>
      </section>

      {/* FAQ */}
      <section className="faq-section" id="faq">
        <div className="section-tag">Preguntas frecuentes</div>
        <h2 className="section-title">Todo lo que necesitas saber</h2>
        <div className="faq-items">
          {faqs.map((f, i) => (
            <div key={i} className={`faq-item${faqOpen === i ? ' open' : ''}`}>
              <div className="faq-q" onClick={() => setFaqOpen(faqOpen === i ? null : i)}>{f.q} <span className="faq-arrow">+</span></div>
              <div className="faq-a">{f.a}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA FINAL */}
      <section className="cta-final">
        <h2>Tu operación merece<br /><em>mejores herramientas</em></h2>
        <p>Crea tu cuenta y descubre cómo TraceLog simplifica tu operación.</p>
        <div className="cta-final-btns">
          <Link to="/register" className="btn-primary btn-lg">Crear cuenta →</Link>
          <a href="#precios" onClick={scrollTo('precios')} className="btn-ghost btn-lg">Ver precios</a>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <div className="footer-logo">Trace<span>Log</span></div>
        <div className="footer-links">
          <a href="#modulos" onClick={scrollTo('modulos')}>Módulos</a>
          <a href="#precios" onClick={scrollTo('precios')}>Precios</a>
          <Link to="/login">Iniciar sesión</Link>
          <Link to="/register">Crear cuenta</Link>
        </div>
        <div className="footer-copy">© 2026 TraceLog · Bogotá, Colombia</div>
      </footer>
    </div>
  )
}
