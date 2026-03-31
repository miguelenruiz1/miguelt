import { useState, useRef, useCallback } from 'react'
import {
  Upload, Search, FileText, Image, Film, FileSpreadsheet,
  Trash2, ExternalLink, X, Filter, FolderOpen, Pencil, Check,
  Link2, Monitor, Loader2,
} from 'lucide-react'
import { useMediaFiles, useUploadMedia, useUpdateMedia, useDeleteMedia, useMediaReferenceCounts } from '@/hooks/useMedia'
import { mediaFileUrl } from '@/lib/media-api'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'
import { Button } from '@/components/ui/button'
import type { MediaFile } from '@/types/api'

// ── Categories ──────────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: '', label: 'Todas' },
  { value: 'general', label: 'General' },
  { value: 'compliance', label: 'Cumplimiento' },
  { value: 'custody_proof', label: 'Custodia' },
  { value: 'customs', label: 'Aduanas' },
  { value: 'transport', label: 'Transporte' },
  { value: 'certificate', label: 'Certificados' },
]

const CATEGORY_COLORS: Record<string, string> = {
  general: 'bg-slate-100 text-slate-600',
  compliance: 'bg-emerald-50 text-emerald-700',
  custody_proof: 'bg-blue-50 text-blue-700',
  customs: 'bg-orange-50 text-orange-700',
  transport: 'bg-amber-50 text-amber-700',
  certificate: 'bg-purple-50 text-purple-700',
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function fileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return Image
  if (contentType.startsWith('video/')) return Film
  if (contentType.includes('spreadsheet') || contentType.includes('csv')) return FileSpreadsheet
  return FileText
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function MediaPage() {
  const toast = useToast()
  const confirm = useConfirm()
  const inputRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [offset, setOffset] = useState(0)
  const [editingId, setEditingId] = useState<string | null>(null)
  const limit = 24

  const { data, isLoading } = useMediaFiles({ search: search || undefined, category: category || undefined, offset, limit })
  const uploadMedia = useUploadMedia()
  const updateMedia = useUpdateMedia()
  const deleteMedia = useDeleteMedia()

  const files = data?.items ?? []
  const total = data?.total ?? 0
  const fileIds = files.map(f => f.id)
  const { data: refCounts } = useMediaReferenceCounts(fileIds)

  const handleUpload = useCallback(async (fileList: FileList | null) => {
    if (!fileList?.length) return
    for (const file of Array.from(fileList)) {
      try {
        await uploadMedia.mutateAsync({ file, category: category || 'general' })
        toast.success(`"${file.name}" subido`)
      } catch (err: any) {
        toast.error(`Error subiendo ${file.name}: ${err?.message ?? 'desconocido'}`)
      }
    }
  }, [uploadMedia, category, toast])

  const handleDelete = useCallback(async (file: MediaFile) => {
    const ok = await confirm({ title: 'Eliminar archivo', message: `Eliminar "${file.title || file.original_filename}"? Si esta vinculado a parcelas o registros, esos vinculos se romperan.`, confirmLabel: 'Eliminar', destructive: true })
    if (!ok) return
    try {
      await deleteMedia.mutateAsync(file.id)
      toast.success('Archivo eliminado')
    } catch {
      toast.error('Error eliminando archivo')
    }
  }, [deleteMedia, toast, confirm])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50">
            <FolderOpen className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Biblioteca de Media</h1>
            <p className="text-sm text-slate-500">{total} archivo{total !== 1 ? 's' : ''} en el sistema</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input ref={inputRef} type="file" className="hidden" multiple
            onChange={(e) => { handleUpload(e.target.files); if (inputRef.current) inputRef.current.value = '' }} />
          <Button onClick={() => inputRef.current?.click()} loading={uploadMedia.isPending}>
            <Monitor className="h-4 w-4 mr-1.5" /> Subir desde PC
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input type="text" placeholder="Buscar archivos..." value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Filter className="h-4 w-4 text-slate-400" />
          {CATEGORIES.map(c => (
            <button key={c.value} onClick={() => { setCategory(c.value); setOffset(0) }}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                category === c.value ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : files.length === 0 ? (
        <button onClick={() => inputRef.current?.click()}
          className="w-full flex flex-col items-center justify-center py-20 text-slate-400 hover:text-primary/60 transition-colors group">
          <Upload className="h-12 w-12 mb-3 group-hover:text-primary/40" />
          <p className="font-medium text-slate-500">No hay archivos</p>
          <p className="text-sm mt-1">Haz click para subir desde tu PC</p>
        </button>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
                <th className="px-4 py-3 w-12"></th>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3">Tipo Doc.</th>
                <th className="px-4 py-3 text-right">Tamano</th>
                <th className="px-4 py-3">Hash</th>
                <th className="px-4 py-3 text-center">Usos</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {files.map(file => (
                <FileRow
                  key={file.id}
                  file={file}
                  refCount={refCounts?.[file.id] ?? 0}
                  isEditing={editingId === file.id}
                  onEdit={() => setEditingId(file.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSave={async (data) => {
                    await updateMedia.mutateAsync({ id: file.id, ...data })
                    toast.success('Archivo actualizado')
                    setEditingId(null)
                  }}
                  onDelete={() => handleDelete(file)}
                  saving={updateMedia.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <Button variant="ghost" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            Anterior
          </Button>
          <span className="text-xs text-slate-500">{offset + 1}–{Math.min(offset + limit, total)} de {total}</span>
          <Button variant="ghost" size="sm" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            Siguiente
          </Button>
        </div>
      )}
    </div>
  )
}

// ── File Row ────────────────────────────────────────────────────────────────

function FileRow({ file, refCount, isEditing, onEdit, onCancelEdit, onSave, onDelete, saving }: {
  file: MediaFile
  refCount: number
  isEditing: boolean
  onEdit: () => void
  onCancelEdit: () => void
  onSave: (data: { title?: string; category?: string; document_type?: string; description?: string }) => Promise<void>
  onDelete: () => void
  saving: boolean
}) {
  const Icon = fileIcon(file.content_type)
  const isImg = file.content_type.startsWith('image/')
  const fullUrl = mediaFileUrl(file.url)

  const [title, setTitle] = useState(file.title || file.original_filename)
  const [cat, setCat] = useState(file.category)
  const [docType, setDocType] = useState(file.document_type || '')
  const [desc, setDesc] = useState(file.description || '')

  if (isEditing) {
    return (
      <tr className="bg-primary/[0.02]">
        <td className="px-4 py-2">
          <div className="h-8 w-8 rounded-lg overflow-hidden bg-slate-50 flex items-center justify-center">
            {isImg ? <img src={fullUrl} alt="" className="h-full w-full object-cover" /> : <Icon className="h-4 w-4 text-slate-300" />}
          </div>
        </td>
        <td className="px-4 py-2">
          <input value={title} onChange={e => setTitle(e.target.value)}
            className="w-full px-2 py-1 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
          <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Descripcion..."
            className="w-full px-2 py-1 mt-1 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary/20 outline-none text-slate-500" />
        </td>
        <td className="px-4 py-2">
          <select value={cat} onChange={e => setCat(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none">
            {CATEGORIES.filter(c => c.value).map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </td>
        <td className="px-4 py-2">
          <input value={docType} onChange={e => setDocType(e.target.value)} placeholder="Tipo..."
            className="w-full px-2 py-1 text-xs border border-slate-200 rounded-lg outline-none" />
        </td>
        <td className="px-4 py-2 text-right text-xs text-slate-400">{fmtSize(file.file_size)}</td>
        <td className="px-4 py-2"></td>
        <td className="px-4 py-2"></td>
        <td className="px-4 py-2"></td>
        <td className="px-4 py-2 text-right">
          <div className="flex items-center gap-1 justify-end">
            <button onClick={async () => { await onSave({ title, category: cat, document_type: docType || undefined, description: desc || undefined }) }}
              disabled={saving}
              className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
            </button>
            <button onClick={onCancelEdit} className="p-1.5 text-slate-400 hover:bg-slate-100 rounded-lg">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <tr className="hover:bg-slate-50/50 transition-colors">
      {/* Thumbnail */}
      <td className="px-4 py-2.5">
        <div className="h-8 w-8 rounded-lg overflow-hidden bg-slate-50 flex items-center justify-center">
          {isImg ? <img src={fullUrl} alt="" className="h-full w-full object-cover" /> : <Icon className="h-4 w-4 text-slate-300" />}
        </div>
      </td>
      {/* Name + description */}
      <td className="px-4 py-2.5">
        <p className="text-sm font-medium text-slate-800 truncate max-w-[250px]">{file.title || file.original_filename}</p>
        {file.description && <p className="text-[11px] text-slate-400 truncate max-w-[250px]">{file.description}</p>}
        <p className="text-[10px] text-slate-300 font-mono">{file.original_filename}</p>
      </td>
      {/* Category */}
      <td className="px-4 py-2.5">
        <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold ${CATEGORY_COLORS[file.category] ?? CATEGORY_COLORS.general}`}>
          {CATEGORIES.find(c => c.value === file.category)?.label ?? file.category}
        </span>
      </td>
      {/* Document type */}
      <td className="px-4 py-2.5">
        {file.document_type ? (
          <span className="text-xs text-slate-500">{file.document_type}</span>
        ) : (
          <span className="text-xs text-slate-300">—</span>
        )}
      </td>
      {/* Size */}
      <td className="px-4 py-2.5 text-right">
        <span className="text-xs text-slate-500 tabular-nums">{fmtSize(file.file_size)}</span>
      </td>
      {/* Hash */}
      <td className="px-4 py-2.5">
        <span className="text-[10px] font-mono text-slate-400" title={file.file_hash}>{file.file_hash.slice(0, 10)}...</span>
      </td>
      {/* Reference count */}
      <td className="px-4 py-2.5 text-center">
        {refCount > 0 ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-100">
            <Link2 className="h-2.5 w-2.5" /> {refCount}
          </span>
        ) : (
          <span className="text-[10px] text-slate-300">0</span>
        )}
      </td>
      {/* Date */}
      <td className="px-4 py-2.5">
        <span className="text-xs text-slate-400">{fmtDate(file.created_at)}</span>
      </td>
      {/* Actions */}
      <td className="px-4 py-2.5 text-right">
        <div className="flex items-center gap-0.5 justify-end">
          <a href={fullUrl} target="_blank" rel="noopener noreferrer"
            className="p-1.5 text-slate-400 hover:text-primary hover:bg-primary/10 rounded-lg" title="Abrir">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <button onClick={onEdit} className="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg" title="Editar">
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button onClick={onDelete} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg" title="Eliminar">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </td>
    </tr>
  )
}
