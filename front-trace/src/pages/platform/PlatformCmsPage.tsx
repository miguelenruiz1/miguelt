import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  FileText, Plus, Search, Copy, Globe, Trash2, Eye, EyeOff, MoreHorizontal,
} from 'lucide-react'
import {
  useCmsPages, useCreateCmsPage, useDeleteCmsPage,
  usePublishCmsPage, useUnpublishCmsPage, useDuplicateCmsPage,
} from '@/hooks/useCms'

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  draft:     { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Borrador' },
  published: { bg: 'bg-green-100', text: 'text-green-700', label: 'Publicada' },
  archived:  { bg: 'bg-secondary', text: 'text-muted-foreground', label: 'Archivada' },
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function PlatformCmsPage() {
  const navigate = useNavigate()
  const { data: pages, isLoading } = useCmsPages()
  const createPage = useCreateCmsPage()
  const deletePage = useDeleteCmsPage()
  const publishPage = usePublishCmsPage()
  const unpublishPage = useUnpublishCmsPage()
  const duplicatePage = useDuplicateCmsPage()

  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newSlug, setNewSlug] = useState('')
  const [newLang, setNewLang] = useState('es')
  const [openMenu, setOpenMenu] = useState<string | null>(null)

  const filtered = (pages ?? []).filter(p =>
    p.title.toLowerCase().includes(search.toLowerCase()) ||
    p.slug.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreate = async () => {
    if (!newTitle.trim()) return
    const page = await createPage.mutateAsync({
      title: newTitle.trim(),
      slug: newSlug.trim() || slugify(newTitle),
      lang: newLang,
    })
    setShowCreate(false)
    setNewTitle('')
    setNewSlug('')
    navigate(`/platform/cms/${page.id}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Landing Pages</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Gestiona las paginas publicas del sitio con el editor visual.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" /> Nueva pagina
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Buscar por titulo o slug..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2.5 text-sm bg-card border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>{pages?.length === 0 ? 'No hay paginas creadas aun.' : 'Sin resultados.'}</p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Titulo</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Slug</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Estado</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Secciones</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Creada</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(page => {
                const badge = STATUS_BADGE[page.status] ?? STATUS_BADGE.draft
                return (
                  <tr key={page.id} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3">
                      <Link to={`/platform/cms/${page.id}`} className="font-medium text-foreground hover:text-primary transition-colors">
                        {page.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                      /p/{page.slug}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{page.section_count}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">
                      {new Date(page.created_at).toLocaleDateString('es-CO')}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="relative inline-block">
                        <button
                          onClick={() => setOpenMenu(openMenu === page.id ? null : page.id)}
                          className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                        >
                          <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                        </button>
                        {openMenu === page.id && (
                          <>
                            <div className="fixed inset-0 z-40" onClick={() => setOpenMenu(null)} />
                            <div className="absolute right-0 top-full mt-1 w-48 bg-card border border-border rounded-xl shadow-lg z-50 py-1">
                              <Link
                                to={`/platform/cms/${page.id}`}
                                onClick={() => setOpenMenu(null)}
                                className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors w-full"
                              >
                                <FileText className="h-4 w-4" /> Editar
                              </Link>
                              {page.status === 'published' && (
                                <a
                                  href={`/p/${page.slug}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={() => setOpenMenu(null)}
                                  className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors w-full"
                                >
                                  <Globe className="h-4 w-4" /> Ver publica
                                </a>
                              )}
                              {page.status === 'draft' ? (
                                <button
                                  onClick={() => { publishPage.mutate(page.id); setOpenMenu(null) }}
                                  className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors w-full text-left"
                                >
                                  <Eye className="h-4 w-4" /> Publicar
                                </button>
                              ) : page.status === 'published' ? (
                                <button
                                  onClick={() => { unpublishPage.mutate(page.id); setOpenMenu(null) }}
                                  className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors w-full text-left"
                                >
                                  <EyeOff className="h-4 w-4" /> Despublicar
                                </button>
                              ) : null}
                              <button
                                onClick={() => { duplicatePage.mutate(page.id); setOpenMenu(null) }}
                                className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors w-full text-left"
                              >
                                <Copy className="h-4 w-4" /> Duplicar
                              </button>
                              <div className="h-px bg-border my-1" />
                              <button
                                onClick={() => {
                                  if (confirm('Eliminar esta pagina?')) {
                                    deletePage.mutate(page.id)
                                  }
                                  setOpenMenu(null)
                                }}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors w-full text-left"
                              >
                                <Trash2 className="h-4 w-4" /> Eliminar
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreate(false)}>
          <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-foreground mb-4">Nueva pagina</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Titulo</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={e => { setNewTitle(e.target.value); if (!newSlug || newSlug === slugify(newTitle)) setNewSlug(slugify(e.target.value)) }}
                  placeholder="Mi Landing Page"
                  className="w-full px-3 py-2.5 text-sm bg-background border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Slug</label>
                <div className="flex items-center gap-1 text-sm text-muted-foreground mb-1">
                  <span>/p/</span>
                </div>
                <input
                  type="text"
                  value={newSlug}
                  onChange={e => setNewSlug(e.target.value)}
                  placeholder="mi-landing-page"
                  className="w-full px-3 py-2.5 text-sm bg-background border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none font-mono"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Idioma</label>
                <select
                  value={newLang}
                  onChange={e => setNewLang(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm bg-background border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
                >
                  <option value="es">Espanol</option>
                  <option value="en">English</option>
                  <option value="pt">Portugues</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm font-medium rounded-xl border border-border hover:bg-muted transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreate}
                disabled={!newTitle.trim() || createPage.isPending}
                className="px-4 py-2 text-sm font-medium rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {createPage.isPending ? 'Creando...' : 'Crear pagina'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
