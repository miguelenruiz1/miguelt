import { Link } from 'react-router-dom'
import { safeHtml } from '@/lib/safe-html'

interface HeroCta {
  text: string
  href: string
  variant?: 'primary' | 'ghost'
}

interface HeroStat {
  value: string
  label: string
}

interface HeroConfig {
  tag?: string
  headline?: string
  subtitle?: string
  ctas?: HeroCta[]
  stats?: HeroStat[]
  background_image?: string
  background_gradient?: string
}

export function HeroBlock({ config }: { config: HeroConfig }) {
  const bg: React.CSSProperties = {}
  if (config.background_image) {
    bg.backgroundImage = `url(${config.background_image})`
    bg.backgroundSize = 'cover'
    bg.backgroundPosition = 'center'
  } else if (config.background_gradient) {
    bg.background = config.background_gradient
  }

  return (
    <div className="lp" style={bg}>
      <section className="hero" style={{ gridTemplateColumns: '1fr', maxWidth: 900, textAlign: 'center', margin: '0 auto' }}>
        <div>
          {config.tag && (
            <div className="hero-tag" style={{ justifyContent: 'center', margin: '0 auto 24px' }}>
              <span className="nav-logo-dot" />{config.tag}
            </div>
          )}
          {config.headline && (
            <h1 dangerouslySetInnerHTML={safeHtml(config.headline.replace(/\*(.*?)\*/g, '<em>$1</em>'))} />
          )}
          {config.subtitle && <p className="hero-sub" style={{ maxWidth: '100%', margin: '0 auto 36px' }}>{config.subtitle}</p>}
          {config.ctas && config.ctas.length > 0 && (
            <div className="hero-ctas" style={{ justifyContent: 'center' }}>
              {config.ctas.map((cta, i) => {
                const cls = cta.variant === 'ghost' ? 'btn-ghost btn-lg' : 'btn-primary btn-lg'
                return cta.href.startsWith('/') ? (
                  <Link key={i} to={cta.href} className={cls}>{cta.text}</Link>
                ) : (
                  <a key={i} href={cta.href} className={cls}>{cta.text}</a>
                )
              })}
            </div>
          )}
          {config.stats && config.stats.length > 0 && (
            <div className="hero-stats" style={{ justifyContent: 'center' }}>
              {config.stats.map((s, i) => (
                <div key={i} className="stat">
                  <span className="stat-num">{s.value}</span>
                  <span className="stat-label">{s.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
