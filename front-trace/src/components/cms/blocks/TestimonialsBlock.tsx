interface Testimonial {
  quote: string
  author: string
  role?: string
  avatar?: string
}

interface TestimonialsConfig {
  heading?: string
  subtitle?: string
  testimonials: Testimonial[]
}

export function TestimonialsBlock({ config }: { config: TestimonialsConfig }) {
  return (
    <div className="lp">
      <section style={{ padding: '100px 5%', maxWidth: 1300, margin: '0 auto' }}>
        {config.heading && (
          <>
            <div className="section-tag">Testimonios</div>
            <h2 className="section-title">{config.heading}</h2>
          </>
        )}
        {config.subtitle && <p className="section-sub">{config.subtitle}</p>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20, marginTop: 48 }}>
          {config.testimonials?.map((t, i) => (
            <div
              key={i}
              style={{
                background: 'var(--bg2)',
                border: '1px solid var(--border)',
                borderRadius: 16,
                padding: '28px 24px',
                transition: 'border-color 0.3s',
              }}
            >
              <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.7, marginBottom: 20, fontStyle: 'italic' }}>
                &ldquo;{t.quote}&rdquo;
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {t.avatar ? (
                  <img src={t.avatar} alt={t.author} style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' }} />
                ) : (
                  <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--green-dim)', border: '1px solid var(--border2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: 'var(--green)' }}>
                    {t.author?.[0]?.toUpperCase()}
                  </div>
                )}
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--white)' }}>{t.author}</div>
                  {t.role && <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.role}</div>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
