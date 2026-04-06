import { Link } from 'react-router-dom'
import { safeHtml } from '@/lib/safe-html'

interface CtaCta {
  text: string
  href: string
  variant?: 'primary' | 'ghost'
}

interface CtaConfig {
  heading?: string
  subtitle?: string
  ctas?: CtaCta[]
  background_gradient?: string
}

export function CtaBlock({ config }: { config: CtaConfig }) {
  const style: React.CSSProperties = config.background_gradient
    ? { background: config.background_gradient }
    : {}

  return (
    <div className="lp" style={style}>
      <section className="cta-final">
        {config.heading && (
          <h2 dangerouslySetInnerHTML={safeHtml(config.heading.replace(/\*(.*?)\*/g, '<em>$1</em>'))} />
        )}
        {config.subtitle && <p>{config.subtitle}</p>}
        {config.ctas && config.ctas.length > 0 && (
          <div className="cta-final-btns">
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
      </section>
    </div>
  )
}
