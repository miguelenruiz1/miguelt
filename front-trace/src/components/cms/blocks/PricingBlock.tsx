import { Link } from 'react-router-dom'

interface PlanFeature {
  text: string
}

interface PricingPlan {
  name: string
  description?: string
  price: string
  price_suffix?: string
  price_note?: string
  features: PlanFeature[]
  cta_text?: string
  cta_href?: string
  is_popular?: boolean
  is_outline?: boolean
}

interface PricingConfig {
  heading?: string
  subtitle?: string
  plans: PricingPlan[]
  note?: string
}

export function PricingBlock({ config }: { config: PricingConfig }) {
  return (
    <div className="lp">
      <section className="precios-section">
        <div className="precios-inner">
          {config.heading && (
            <>
              <div className="section-tag">Precios</div>
              <h2 className="section-title">{config.heading}</h2>
            </>
          )}
          {config.subtitle && <p className="section-sub">{config.subtitle}</p>}
          <div
            className="precios-grid"
            style={{ gridTemplateColumns: `repeat(${Math.min(config.plans?.length ?? 3, 5)}, 1fr)` }}
          >
            {config.plans?.map((p, i) => (
              <div key={i} className={`precio-card${p.is_popular ? ' popular' : ''}`}>
                {p.is_popular && <div className="popular-badge">Mas popular</div>}
                <div className="plan-name">{p.name}</div>
                {p.description && <div className="plan-para">{p.description}</div>}
                <div className="plan-price">
                  <span className="plan-cop">{p.price}</span>
                  {p.price_suffix && <span className="plan-mes"> {p.price_suffix}</span>}
                </div>
                {p.price_note && <div className="plan-usd">{p.price_note}</div>}
                <div className="plan-divider" />
                <div className="plan-features">
                  {p.features?.map((f, j) => (
                    <div key={j} className="pf-item">
                      <span className="pf-check">&#10003;</span>{f.text}
                    </div>
                  ))}
                </div>
                {p.cta_text && (
                  p.cta_href?.startsWith('/') ? (
                    <Link to={p.cta_href} className={`plan-cta${p.is_popular ? ' cta-primary' : p.is_outline ? ' cta-outline' : ''}`}>
                      {p.cta_text}
                    </Link>
                  ) : (
                    <a href={p.cta_href ?? '#'} className={`plan-cta${p.is_popular ? ' cta-primary' : p.is_outline ? ' cta-outline' : ''}`}>
                      {p.cta_text}
                    </a>
                  )
                )}
              </div>
            ))}
          </div>
          {config.note && (
            <div className="precios-note" dangerouslySetInnerHTML={{ __html: config.note }} />
          )}
        </div>
      </section>
    </div>
  )
}
