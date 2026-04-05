import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Eye, EyeOff, Globe, Save, Plus, Trash2, GripVertical,
  ChevronDown, ChevronUp, Code, Search as SearchIcon, FileText,
} from 'lucide-react'
import {
  useCmsPage, useUpdateCmsPage, usePublishCmsPage, useUnpublishCmsPage,
  useAddCmsSection, useUpdateCmsSection, useDeleteCmsSection, useReorderCmsSections,
  useCreateCmsScript, useUpdateCmsScript, useDeleteCmsScript,
} from '@/hooks/useCms'
import { AVAILABLE_BLOCKS } from '@/components/cms/BlockRenderer'
import type { CmsPage, CmsSection, CmsScript } from '@/lib/cms-api'

// ─── Tab types ──────────────────────────────────────────────────────────────

type Tab = 'contenido' | 'seo' | 'scripts' | 'preview'

// ─── SectionEditor ──────────────────────────────────────────────────────────

function SectionEditor({ section, pageId }: { section: CmsSection; pageId: string }) {
  const [expanded, setExpanded] = useState(false)
  const [config, setConfig] = useState(JSON.stringify(section.config, null, 2))
  const [anchorId, setAnchorId] = useState(section.anchor_id ?? '')
  const [cssClass, setCssClass] = useState(section.css_class ?? '')
  const updateSection = useUpdateCmsSection(pageId)
  const deleteSection = useDeleteCmsSection(pageId)

  const blockInfo = AVAILABLE_BLOCKS.find(b => b.type === section.block_type)

  const handleSave = () => {
    try {
      const parsed = JSON.parse(config)
      updateSection.mutate({
        sectionId: section.id,
        data: { config: parsed, anchor_id: anchorId || undefined, css_class: cssClass || undefined },
      })
    } catch {
      alert('JSON invalido en la configuracion')
    }
  }

  const toggleVisibility = () => {
    updateSection.mutate({
      sectionId: section.id,
      data: { is_visible: !section.is_visible },
    })
  }

  return (
    <div className="border border-border rounded-xl bg-card overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab shrink-0" />
        <span className="text-lg">{blockInfo?.icon ?? '?'}</span>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-foreground">{blockInfo?.label ?? section.block_type}</span>
          {section.anchor_id && (
            <span className="ml-2 text-xs text-muted-foreground font-mono">#{section.anchor_id}</span>
          )}
        </div>
        <button
          onClick={toggleVisibility}
          className="p-1.5 rounded-lg hover:bg-muted transition-colors"
          title={section.is_visible ? 'Ocultar' : 'Mostrar'}
        >
          {section.is_visible ? <Eye className="h-4 w-4 text-green-600" /> : <EyeOff className="h-4 w-4 text-muted-foreground" />}
        </button>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1.5 rounded-lg hover:bg-muted transition-colors"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        <button
          onClick={() => { if (confirm('Eliminar esta seccion?')) deleteSection.mutate(section.id) }}
          className="p-1.5 rounded-lg hover:bg-muted transition-colors text-red-500"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {expanded && (
        <div className="border-t border-border px-4 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Anchor ID</label>
              <input
                type="text"
                value={anchorId}
                onChange={e => setAnchorId(e.target.value)}
                placeholder="seccion-hero"
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">CSS Class</label>
              <input
                type="text"
                value={cssClass}
                onChange={e => setCssClass(e.target.value)}
                placeholder="my-custom-class"
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Configuracion (JSON)</label>
            <textarea
              value={config}
              onChange={e => setConfig(e.target.value)}
              rows={12}
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20 font-mono"
            />
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={updateSection.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Save className="h-4 w-4" /> {updateSection.isPending ? 'Guardando...' : 'Guardar seccion'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── AddSectionDialog ───────────────────────────────────────────────────────

function AddSectionDialog({ pageId, onClose }: { pageId: string; onClose: () => void }) {
  const addSection = useAddCmsSection(pageId)

  const handleAdd = async (blockType: string) => {
    await addSection.mutateAsync({ block_type: blockType, config: {} })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-foreground mb-4">Agregar seccion</h3>
        <div className="grid grid-cols-2 gap-3 max-h-[400px] overflow-y-auto">
          {AVAILABLE_BLOCKS.map(block => (
            <button
              key={block.type}
              onClick={() => handleAdd(block.type)}
              disabled={addSection.isPending}
              className="flex items-start gap-3 p-3 text-left border border-border rounded-xl hover:bg-muted/50 hover:border-primary/30 transition-colors"
            >
              <span className="text-2xl shrink-0">{block.icon}</span>
              <div>
                <div className="text-sm font-medium text-foreground">{block.label}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{block.description}</div>
              </div>
            </button>
          ))}
        </div>
        <div className="flex justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-xl border border-border hover:bg-muted transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── ScriptEditor ───────────────────────────────────────────────────────────

function ScriptRow({ script, pageId }: { script: CmsScript; pageId: string }) {
  const [editing, setEditing] = useState(false)
  const [src, setSrc] = useState(script.src ?? '')
  const [inline, setInline] = useState(script.inline_code ?? '')
  const [placement, setPlacement] = useState(script.placement)
  const [strategy, setStrategy] = useState(script.load_strategy)
  const [active, setActive] = useState(script.is_active)
  const updateScript = useUpdateCmsScript(pageId)
  const deleteScript = useDeleteCmsScript(pageId)

  const handleSave = () => {
    updateScript.mutate({
      scriptId: script.id,
      data: {
        src: src || undefined,
        inline_code: inline || undefined,
        placement,
        load_strategy: strategy,
        is_active: active,
      },
    })
    setEditing(false)
  }

  return (
    <div className="border border-border rounded-xl bg-card p-4">
      <div className="flex items-center gap-3">
        <Code className="h-4 w-4 text-muted-foreground shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-foreground font-mono truncate block">
            {script.src ?? 'Inline script'}
          </span>
          <span className="text-xs text-muted-foreground">
            {script.placement} / {script.load_strategy} {!script.is_active && '(inactivo)'}
          </span>
        </div>
        <button onClick={() => setEditing(!editing)} className="text-xs text-primary hover:underline">
          {editing ? 'Cerrar' : 'Editar'}
        </button>
        <button
          onClick={() => { if (confirm('Eliminar script?')) deleteScript.mutate(script.id) }}
          className="p-1 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {editing && (
        <div className="mt-4 space-y-3 border-t border-border pt-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">URL (src)</label>
            <input
              value={src}
              onChange={e => setSrc(e.target.value)}
              placeholder="https://cdn.example.com/script.js"
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Codigo inline</label>
            <textarea
              value={inline}
              onChange={e => setInline(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none font-mono"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Ubicacion</label>
              <select value={placement} onChange={e => setPlacement(e.target.value as any)} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none">
                <option value="head">Head</option>
                <option value="body_start">Body (inicio)</option>
                <option value="body_end">Body (final)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Carga</label>
              <select value={strategy} onChange={e => setStrategy(e.target.value as any)} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none">
                <option value="async">Async</option>
                <option value="defer">Defer</option>
                <option value="blocking">Blocking</option>
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} className="rounded" />
                Activo
              </label>
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={handleSave} disabled={updateScript.isPending} className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              Guardar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main editor page ───────────────────────────────────────────────────────

export function PlatformCmsEditorPage() {
  const { pageId } = useParams<{ pageId: string }>()
  const { data: page, isLoading } = useCmsPage(pageId ?? '')
  const updatePage = useUpdateCmsPage(pageId ?? '')
  const publishPage = usePublishCmsPage()
  const unpublishPage = useUnpublishCmsPage()
  const createScript = useCreateCmsScript(pageId ?? '')

  const [tab, setTab] = useState<Tab>('contenido')
  const [showAddSection, setShowAddSection] = useState(false)
  const [showAddScript, setShowAddScript] = useState(false)

  // Page metadata form
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [navbarConfig, setNavbarConfig] = useState('')
  const [footerConfig, setFooterConfig] = useState('')

  // SEO form
  const [seoTitle, setSeoTitle] = useState('')
  const [seoDesc, setSeoDesc] = useState('')
  const [seoKeywords, setSeoKeywords] = useState('')
  const [ogImage, setOgImage] = useState('')
  const [canonical, setCanonical] = useState('')
  const [robots, setRobots] = useState('')

  // New script form
  const [newScriptSrc, setNewScriptSrc] = useState('')
  const [newScriptInline, setNewScriptInline] = useState('')
  const [newScriptPlacement, setNewScriptPlacement] = useState<'head' | 'body_start' | 'body_end'>('head')

  useEffect(() => {
    if (!page) return
    setTitle(page.title)
    setSlug(page.slug)
    setNavbarConfig(page.navbar_config ? JSON.stringify(page.navbar_config, null, 2) : '{}')
    setFooterConfig(page.footer_config ? JSON.stringify(page.footer_config, null, 2) : '{}')
    setSeoTitle(page.seo_title ?? '')
    setSeoDesc(page.seo_description ?? '')
    setSeoKeywords(page.seo_keywords ?? '')
    setOgImage(page.og_image ?? '')
    setCanonical(page.canonical_url ?? '')
    setRobots(page.robots ?? '')
  }, [page])

  const handleSaveMetadata = () => {
    try {
      const navbar = JSON.parse(navbarConfig)
      const footer = JSON.parse(footerConfig)
      updatePage.mutate({ title, slug, navbar_config: navbar, footer_config: footer })
    } catch {
      alert('JSON invalido en navbar o footer config')
    }
  }

  const handleSaveSeo = () => {
    updatePage.mutate({
      seo_title: seoTitle || undefined,
      seo_description: seoDesc || undefined,
      seo_keywords: seoKeywords || undefined,
      og_image: ogImage || undefined,
      canonical_url: canonical || undefined,
      robots: robots || undefined,
    })
  }

  const handleAddScript = () => {
    createScript.mutate({
      src: newScriptSrc || undefined,
      inline_code: newScriptInline || undefined,
      placement: newScriptPlacement,
    })
    setShowAddScript(false)
    setNewScriptSrc('')
    setNewScriptInline('')
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!page) {
    return (
      <div className="text-center py-24 text-muted-foreground">
        <p>Pagina no encontrada.</p>
        <Link to="/platform/cms" className="text-primary hover:underline mt-2 inline-block">Volver</Link>
      </div>
    )
  }

  const sortedSections = [...page.sections].sort((a, b) => a.position - b.position)

  const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
    draft:     { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Borrador' },
    published: { bg: 'bg-green-100', text: 'text-green-700', label: 'Publicada' },
    archived:  { bg: 'bg-secondary', text: 'text-muted-foreground', label: 'Archivada' },
  }
  const badge = STATUS_BADGE[page.status] ?? STATUS_BADGE.draft

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/platform/cms" className="p-2 rounded-lg hover:bg-muted transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-foreground">{page.title}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-muted-foreground font-mono">/p/{page.slug}</span>
              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
                {badge.label}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {page.status === 'published' && (
            <a
              href={`/p/${page.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-xl border border-border hover:bg-muted transition-colors"
            >
              <Globe className="h-4 w-4" /> Ver publica
            </a>
          )}
          {page.status === 'draft' ? (
            <button
              onClick={() => publishPage.mutate(page.id)}
              disabled={publishPage.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              <Eye className="h-4 w-4" /> Publicar
            </button>
          ) : page.status === 'published' ? (
            <button
              onClick={() => unpublishPage.mutate(page.id)}
              disabled={unpublishPage.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl border border-border hover:bg-muted transition-colors disabled:opacity-50"
            >
              <EyeOff className="h-4 w-4" /> Despublicar
            </button>
          ) : null}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {([
          { key: 'contenido', label: 'Contenido', icon: FileText },
          { key: 'seo', label: 'SEO', icon: SearchIcon },
          { key: 'scripts', label: 'Scripts', icon: Code },
          { key: 'preview', label: 'Vista previa', icon: Eye },
        ] as const).map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'contenido' && (
        <div className="space-y-6">
          {/* Page metadata */}
          <div className="bg-card border border-border rounded-xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-foreground">Metadatos de la pagina</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Titulo</label>
                <input
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Slug</label>
                <input
                  value={slug}
                  onChange={e => setSlug(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20 font-mono"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Navbar config (JSON)</label>
              <textarea
                value={navbarConfig}
                onChange={e => setNavbarConfig(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Footer config (JSON)</label>
              <textarea
                value={footerConfig}
                onChange={e => setFooterConfig(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20 font-mono"
              />
            </div>
            <div className="flex justify-end">
              <button
                onClick={handleSaveMetadata}
                disabled={updatePage.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                <Save className="h-4 w-4" /> {updatePage.isPending ? 'Guardando...' : 'Guardar metadatos'}
              </button>
            </div>
          </div>

          {/* Sections */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Secciones ({sortedSections.length})</h3>
              <button
                onClick={() => setShowAddSection(true)}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-border hover:bg-muted transition-colors"
              >
                <Plus className="h-4 w-4" /> Agregar seccion
              </button>
            </div>
            {sortedSections.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-xl">
                <p className="mb-2">No hay secciones aun.</p>
                <button
                  onClick={() => setShowAddSection(true)}
                  className="text-primary hover:underline text-sm"
                >
                  Agregar la primera seccion
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {sortedSections.map(section => (
                  <SectionEditor key={section.id} section={section} pageId={page.id} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'seo' && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-4 max-w-2xl">
          <h3 className="text-sm font-semibold text-foreground">Configuracion SEO</h3>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Titulo SEO</label>
            <input value={seoTitle} onChange={e => setSeoTitle(e.target.value)} placeholder={page.title} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Meta description</label>
            <textarea value={seoDesc} onChange={e => setSeoDesc(e.target.value)} rows={3} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Keywords</label>
            <input value={seoKeywords} onChange={e => setSeoKeywords(e.target.value)} placeholder="trace, logistics, eudr" className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">OG Image URL</label>
            <input value={ogImage} onChange={e => setOgImage(e.target.value)} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Canonical URL</label>
            <input value={canonical} onChange={e => setCanonical(e.target.value)} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Robots</label>
            <input value={robots} onChange={e => setRobots(e.target.value)} placeholder="index, follow" className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none focus:ring-2 focus:ring-ring/20" />
          </div>
          <div className="flex justify-end">
            <button onClick={handleSaveSeo} disabled={updatePage.isPending} className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Save className="h-4 w-4" /> {updatePage.isPending ? 'Guardando...' : 'Guardar SEO'}
            </button>
          </div>
        </div>
      )}

      {tab === 'scripts' && (
        <div className="space-y-4 max-w-2xl">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Scripts ({page.scripts?.length ?? 0})</h3>
            <button
              onClick={() => setShowAddScript(true)}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-border hover:bg-muted transition-colors"
            >
              <Plus className="h-4 w-4" /> Agregar script
            </button>
          </div>
          {page.scripts?.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-xl">
              <Code className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p>No hay scripts configurados.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {page.scripts?.map(script => (
                <ScriptRow key={script.id} script={script} pageId={page.id} />
              ))}
            </div>
          )}

          {/* Add script modal */}
          {showAddScript && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowAddScript(false)}>
              <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
                <h3 className="text-lg font-semibold text-foreground mb-4">Agregar script</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">URL (src)</label>
                    <input value={newScriptSrc} onChange={e => setNewScriptSrc(e.target.value)} placeholder="https://..." className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none font-mono" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">Codigo inline</label>
                    <textarea value={newScriptInline} onChange={e => setNewScriptInline(e.target.value)} rows={4} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none font-mono" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">Ubicacion</label>
                    <select value={newScriptPlacement} onChange={e => setNewScriptPlacement(e.target.value as any)} className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg outline-none">
                      <option value="head">Head</option>
                      <option value="body_start">Body (inicio)</option>
                      <option value="body_end">Body (final)</option>
                    </select>
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                  <button onClick={() => setShowAddScript(false)} className="px-4 py-2 text-sm font-medium rounded-xl border border-border hover:bg-muted transition-colors">Cancelar</button>
                  <button onClick={handleAddScript} disabled={createScript.isPending} className="px-4 py-2 text-sm font-medium rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                    {createScript.isPending ? 'Agregando...' : 'Agregar'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'preview' && (
        <div className="border border-border rounded-xl overflow-hidden bg-black" style={{ minHeight: 600 }}>
          <iframe
            src={`/p/${page.slug}`}
            className="w-full border-0"
            style={{ height: 'calc(100vh - 220px)', minHeight: 600 }}
            title="Preview"
          />
        </div>
      )}

      {showAddSection && <AddSectionDialog pageId={page.id} onClose={() => setShowAddSection(false)} />}
    </div>
  )
}
