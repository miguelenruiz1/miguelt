import { safeHtml } from '@/lib/safe-html'

interface ImageTextConfig {
  heading?: string
  body?: string
  image_url?: string
  image_position?: 'left' | 'right'
}

export function ImageTextBlock({ config }: { config: ImageTextConfig }) {
  const imageLeft = config.image_position === 'left'

  const imageEl = config.image_url ? (
    <div style={{ flex: 1, minWidth: 280 }}>
      <img
        src={config.image_url}
        alt={config.heading ?? ''}
        style={{ width: '100%', borderRadius: 16, border: '1px solid var(--border)' }}
      />
    </div>
  ) : null

  const textEl = (
    <div style={{ flex: 1, minWidth: 280 }}>
      {config.heading && <h2 className="section-title">{config.heading}</h2>}
      {config.body && (
        <div
          style={{ fontSize: 15, color: 'var(--muted)', lineHeight: 1.7 }}
          dangerouslySetInnerHTML={safeHtml(config.body)}
        />
      )}
    </div>
  )

  return (
    <div className="lp">
      <section style={{ padding: '100px 5%', maxWidth: 1300, margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: 60, alignItems: 'center', flexWrap: 'wrap' }}>
          {imageLeft ? <>{imageEl}{textEl}</> : <>{textEl}{imageEl}</>}
        </div>
      </section>
    </div>
  )
}
