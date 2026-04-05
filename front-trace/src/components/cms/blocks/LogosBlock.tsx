interface LogoItem {
  icon?: string
  name: string
  icon_bg?: string
  icon_color?: string
}

interface LogosConfig {
  label?: string
  logos: LogoItem[]
}

export function LogosBlock({ config }: { config: LogosConfig }) {
  return (
    <div className="lp">
      <div style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="logos-section">
          {config.label && <div className="logos-label">{config.label}</div>}
          <div className="logos-grid">
            {config.logos?.map((l, i) => (
              <div key={i} className="logo-item">
                <div
                  className="logo-icon"
                  style={{
                    background: l.icon_bg ?? 'rgba(0,232,122,0.1)',
                    color: l.icon_color ?? 'var(--green)',
                  }}
                >
                  {l.icon ?? l.name?.[0]}
                </div>
                {l.name}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
