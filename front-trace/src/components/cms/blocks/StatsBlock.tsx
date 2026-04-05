interface StatItem {
  value: string
  label: string
}

interface StatsConfig {
  heading?: string
  subtitle?: string
  stats: StatItem[]
}

export function StatsBlock({ config }: { config: StatsConfig }) {
  return (
    <div className="lp">
      <section style={{ padding: '80px 5%', maxWidth: 1300, margin: '0 auto', textAlign: 'center' }}>
        {config.heading && (
          <>
            <div className="section-tag" style={{ justifyContent: 'center' }}>Datos</div>
            <h2 className="section-title">{config.heading}</h2>
          </>
        )}
        {config.subtitle && <p className="section-sub" style={{ margin: '0 auto 48px' }}>{config.subtitle}</p>}
        <div style={{ display: 'flex', gap: 48, justifyContent: 'center', flexWrap: 'wrap' }}>
          {config.stats?.map((s, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontFamily: "'Inter',system-ui,sans-serif", fontSize: 48, fontWeight: 800, color: 'var(--green)', lineHeight: 1 }}>
                {s.value}
              </span>
              <span style={{ fontSize: 14, color: 'var(--muted)', marginTop: 8 }}>{s.label}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
