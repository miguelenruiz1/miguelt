import { useState, useEffect } from 'react'
import { safeHtml } from '@/lib/safe-html'

interface CountdownConfig {
  heading?: string
  subtitle?: string
  target_date: string
  warning_text?: string
  cta_text?: string
  cta_href?: string
}

export function CountdownBlock({ config }: { config: CountdownConfig }) {
  const [cd, setCd] = useState({ days: 0, hours: 0, mins: 0 })

  useEffect(() => {
    const update = () => {
      const diff = new Date(config.target_date).getTime() - Date.now()
      if (diff <= 0) return
      setCd({
        days: Math.floor(diff / 86400000),
        hours: Math.floor((diff % 86400000) / 3600000),
        mins: Math.floor((diff % 3600000) / 60000),
      })
    }
    update()
    const id = setInterval(update, 60000)
    return () => clearInterval(id)
  }, [config.target_date])

  return (
    <div className="lp">
      <section className="eudr-section">
        <div className="eudr-inner">
          {config.heading && (
            <>
              <div className="section-tag" style={{ justifyContent: 'center' }}>Cuenta regresiva</div>
              <h2 className="section-title" dangerouslySetInnerHTML={safeHtml(config.heading)} />
            </>
          )}
          {config.subtitle && <p style={{ color: 'var(--muted)', marginTop: 12 }}>{config.subtitle}</p>}
          <div className="eudr-countdown">
            <div className="countdown-unit">
              <div className="countdown-num">{cd.days}</div>
              <div className="countdown-label">Dias</div>
            </div>
            <div className="countdown-sep">:</div>
            <div className="countdown-unit">
              <div className="countdown-num">{String(cd.hours).padStart(2, '0')}</div>
              <div className="countdown-label">Horas</div>
            </div>
            <div className="countdown-sep">:</div>
            <div className="countdown-unit">
              <div className="countdown-num">{String(cd.mins).padStart(2, '0')}</div>
              <div className="countdown-label">Minutos</div>
            </div>
          </div>
          {config.warning_text && (
            <div className="eudr-warning" dangerouslySetInnerHTML={safeHtml(config.warning_text)} />
          )}
          {config.cta_text && config.cta_href && (
            <a href={config.cta_href} className="btn-primary btn-lg">{config.cta_text}</a>
          )}
        </div>
      </section>
    </div>
  )
}
