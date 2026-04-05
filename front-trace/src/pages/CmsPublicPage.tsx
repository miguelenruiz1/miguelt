import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCmsPublicPage } from '@/hooks/useCms'
import { BlockRenderer } from '@/components/cms/BlockRenderer'
import type { CmsPage } from '@/lib/cms-api'
import '../pages/landing.css'

// ─── useHead: set document title & meta tags ────────────────────────────────

function useHead(page: CmsPage | null | undefined) {
  useEffect(() => {
    if (!page) return

    const prev = document.title
    document.title = page.seo_title || page.title

    const setMeta = (name: string, content: string | undefined) => {
      if (!content) return
      let el = document.querySelector(`meta[name="${name}"]`) as HTMLMetaElement | null
      if (!el) {
        el = document.createElement('meta')
        el.name = name
        document.head.appendChild(el)
      }
      el.content = content
    }

    setMeta('description', page.seo_description)
    setMeta('keywords', page.seo_keywords)
    setMeta('robots', page.robots)

    // OG image
    if (page.og_image) {
      let og = document.querySelector('meta[property="og:image"]') as HTMLMetaElement | null
      if (!og) {
        og = document.createElement('meta')
        og.setAttribute('property', 'og:image')
        document.head.appendChild(og)
      }
      og.content = page.og_image
    }

    // Canonical
    if (page.canonical_url) {
      let link = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null
      if (!link) {
        link = document.createElement('link')
        link.rel = 'canonical'
        document.head.appendChild(link)
      }
      link.href = page.canonical_url
    }

    return () => {
      document.title = prev
    }
  }, [page])
}

// ─── useScripts: inject page scripts into head/body ─────────────────────────

function useScripts(page: CmsPage | null | undefined) {
  useEffect(() => {
    if (!page?.scripts) return

    const injected: HTMLScriptElement[] = []

    for (const script of page.scripts) {
      if (!script.is_active) continue

      const el = document.createElement('script')
      if (script.src) {
        el.src = script.src
      }
      if (script.inline_code) {
        el.textContent = script.inline_code
      }
      if (script.load_strategy === 'async') el.async = true
      if (script.load_strategy === 'defer') el.defer = true

      const target = script.placement === 'head' ? document.head : document.body
      target.appendChild(el)
      injected.push(el)
    }

    return () => {
      for (const el of injected) {
        el.parentNode?.removeChild(el)
      }
    }
  }, [page])
}

// ─── Navbar renderer ────────────────────────────────────────────────────────

function CmsNavbar({ config }: { config: Record<string, any> }) {
  const links: { label: string; href: string }[] = config.links ?? []
  const ctas: { text: string; href: string; variant?: string }[] = config.ctas ?? []
  const logo = config.logo_text ?? 'TraceLog'

  return (
    <div className="lp">
      <nav>
        <Link to={config.logo_href ?? '/home'} className="nav-logo">
          <span className="nav-logo-dot" />
          {logo}
        </Link>
        <ul className="nav-links">
          {links.map((l, i) => (
            <li key={i}><a href={l.href}>{l.label}</a></li>
          ))}
        </ul>
        <div className="nav-ctas">
          {ctas.map((c, i) => (
            c.href.startsWith('/') ? (
              <Link key={i} to={c.href} className={c.variant === 'primary' ? 'btn-primary' : 'btn-ghost'}>
                {c.text}
              </Link>
            ) : (
              <a key={i} href={c.href} className={c.variant === 'primary' ? 'btn-primary' : 'btn-ghost'}>
                {c.text}
              </a>
            )
          ))}
        </div>
      </nav>
    </div>
  )
}

// ─── Footer renderer ────────────────────────────────────────────────────────

function CmsFooter({ config }: { config: Record<string, any> }) {
  const links: { label: string; href: string }[] = config.links ?? []
  const logo = config.logo_text ?? 'TraceLog'
  const copy = config.copyright ?? `\u00A9 ${new Date().getFullYear()} TraceLog`

  return (
    <div className="lp">
      <footer>
        <div className="footer-logo">{logo}</div>
        <div className="footer-links">
          {links.map((l, i) => (
            l.href.startsWith('/') ? (
              <Link key={i} to={l.href}>{l.label}</Link>
            ) : (
              <a key={i} href={l.href}>{l.label}</a>
            )
          ))}
        </div>
        <div className="footer-copy">{copy}</div>
      </footer>
    </div>
  )
}

// ─── Main component ─────────────────────────────────────────────────────────

export function CmsPublicPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data: page, isLoading, isError } = useCmsPublicPage(slug ?? '')

  useHead(page)
  useScripts(page)

  if (isLoading) {
    return (
      <div className="lp" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 32, height: 32, border: '3px solid var(--border)',
            borderTopColor: 'var(--green)', borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
          <span style={{ color: 'var(--muted)', fontSize: 14 }}>Cargando...</span>
        </div>
      </div>
    )
  }

  if (isError || page === null) {
    return (
      <div className="lp" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ fontSize: 72, fontWeight: 800, color: 'var(--green)', marginBottom: 16 }}>404</h1>
          <p style={{ color: 'var(--muted)', fontSize: 18, marginBottom: 32 }}>Pagina no encontrada</p>
          <Link to="/home" className="btn-primary btn-lg">Volver al inicio</Link>
        </div>
      </div>
    )
  }

  if (!page) return null

  // Build CSS variables from theme_overrides
  const themeStyle: React.CSSProperties = {}
  if (page.theme_overrides) {
    for (const [k, v] of Object.entries(page.theme_overrides)) {
      (themeStyle as any)[`--${k}`] = v
    }
  }

  const visibleSections = page.sections
    .filter(s => s.is_visible)
    .sort((a, b) => a.position - b.position)

  return (
    <div style={themeStyle}>
      {page.navbar_config && Object.keys(page.navbar_config).length > 0 && (
        <CmsNavbar config={page.navbar_config} />
      )}

      {/* Offset for fixed navbar */}
      {page.navbar_config && <div style={{ paddingTop: 68 }} />}

      {visibleSections.map(section => (
        <BlockRenderer
          key={section.id}
          blockType={section.block_type}
          config={section.config}
          anchorId={section.anchor_id}
          cssClass={section.css_class}
        />
      ))}

      {page.footer_config && Object.keys(page.footer_config).length > 0 && (
        <CmsFooter config={page.footer_config} />
      )}
    </div>
  )
}
