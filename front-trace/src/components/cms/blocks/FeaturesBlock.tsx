interface FeatureItem {
  icon?: string
  title: string
  description: string
}

interface FeaturesConfig {
  heading?: string
  subtitle?: string
  columns?: number
  features: FeatureItem[]
}

export function FeaturesBlock({ config }: { config: FeaturesConfig }) {
  const cols = config.columns ?? 3
  return (
    <div className="lp">
      <section className="modulos-section">
        {config.heading && (
          <>
            <div className="section-tag">Funcionalidades</div>
            <h2 className="section-title">{config.heading}</h2>
          </>
        )}
        {config.subtitle && <p className="section-sub">{config.subtitle}</p>}
        <div
          className="modulos-grid"
          style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
        >
          {config.features?.map((f, i) => (
            <div key={i} className="modulo-card">
              {f.icon && (
                <div className="modulo-icon-wrap" style={{ background: 'rgba(0,232,122,0.08)', borderColor: 'rgba(0,232,122,0.2)' }}>
                  {f.icon}
                </div>
              )}
              <div className="modulo-card-title">{f.title}</div>
              <div className="modulo-card-sub">{f.description}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
