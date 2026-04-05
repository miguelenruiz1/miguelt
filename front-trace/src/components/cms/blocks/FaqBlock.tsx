import { useState } from 'react'

interface FaqItem {
  question: string
  answer: string
}

interface FaqConfig {
  heading?: string
  subtitle?: string
  items: FaqItem[]
}

export function FaqBlock({ config }: { config: FaqConfig }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null)

  return (
    <div className="lp">
      <section className="faq-section">
        {config.heading && (
          <>
            <div className="section-tag">FAQ</div>
            <h2 className="section-title">{config.heading}</h2>
          </>
        )}
        {config.subtitle && <p className="section-sub">{config.subtitle}</p>}
        <div className="faq-items">
          {config.items?.map((item, i) => (
            <div key={i} className={`faq-item${openIdx === i ? ' open' : ''}`}>
              <div className="faq-q" onClick={() => setOpenIdx(openIdx === i ? null : i)}>
                {item.question}
                <span className="faq-arrow">+</span>
              </div>
              <div className="faq-a">{item.answer}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
