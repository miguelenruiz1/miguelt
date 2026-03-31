/**
 * MediaPickerModal — popup to browse the media library, upload new files,
 * and pick one to link to a compliance record or plot.
 *
 * Flow:
 *  1. User clicks "Adjuntar" on a record/plot
 *  2. This modal opens showing ALL files in media-service
 *  3. User can filter by category, search, or upload a new file directly from PC
 *  4. User clicks a file → selects document_type → confirms
 *  5. Only the media_file_id + document_type is sent to compliance-service
 */
import { useRef, useState } from 'react'
import {
  X, Search, Upload, Check, FileText, Loader2,
  FolderOpen, Monitor,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useMediaFiles, useUploadMedia } from '@/hooks/useMedia'
import { mediaFileUrl } from '@/lib/media-api'
import { useToast } from '@/store/toast'
import type { MediaFile } from '@/types/api'
import type { EvidenceDocumentType } from '@/types/compliance'

const CATEGORIES = [
  { key: '', label: 'Todos' },
  { key: 'compliance', label: 'Cumplimiento' },
  { key: 'general', label: 'General' },
  { key: 'custody_proof', label: 'Custodia' },
  { key: 'customs', label: 'Aduanas' },
]

const DOC_TYPES: { value: EvidenceDocumentType; label: string }[] = [
  { value: 'land_title', label: 'Titulo de tierra' },
  { value: 'legal_cert', label: 'Certificado legal' },
  { value: 'deforestation_report', label: 'Reporte deforestacion' },
  { value: 'satellite_image', label: 'Imagen satelital' },
  { value: 'supplier_declaration', label: 'Declaracion proveedor' },
  { value: 'transport_doc', label: 'Doc. transporte' },
  { value: 'geojson_boundary', label: 'Poligono GeoJSON' },
  { value: 'other', label: 'Otro' },
]

interface Props {
  open: boolean
  onClose: () => void
  onSelect: (mediaFileId: string, documentType: EvidenceDocumentType, description?: string) => Promise<void>
  excludeIds?: string[]
}

function isImage(f: MediaFile) {
  return f.content_type.startsWith('image/')
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function MediaPickerModal({ open, onClose, onSelect, excludeIds = [] }: Props) {
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<MediaFile | null>(null)
  const [docType, setDocType] = useState<EvidenceDocumentType>('other')
  const [description, setDescription] = useState('')
  const [linking, setLinking] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const toast = useToast()
  const uploadMut = useUploadMedia()

  const { data, isLoading } = useMediaFiles({
    category: category || undefined,
    search: search || undefined,
    limit: 100,
  })
  const files = (data as any)?.items ?? []
  const filtered = files.filter((f: MediaFile) => !excludeIds.includes(f.id))

  if (!open) return null

  async function handleConfirm() {
    if (!selected) return
    setLinking(true)
    try {
      await onSelect(selected.id, docType, description || undefined)
      toast.success(`"${selected.original_filename}" vinculado como ${DOC_TYPES.find(d => d.value === docType)?.label}`)
      setSelected(null)
      setDescription('')
      onClose()
    } catch (err: any) {
      toast.error(err?.body?.detail ?? err?.message ?? 'Error al vincular')
    } finally {
      setLinking(false)
    }
  }

  async function handleFileFromPC(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    // Reset input so same file can be re-selected
    e.target.value = ''
    try {
      const mediaFile = await uploadMut.mutateAsync({
        file,
        category: 'compliance',
        title: file.name,
      })
      toast.success(`"${file.name}" subido a media`)
      // Auto-select the newly uploaded file
      setSelected(mediaFile)
    } catch (err: any) {
      toast.error(err?.body?.detail ?? err?.message ?? 'Error al subir archivo')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-bold text-slate-900">Biblioteca de Media</h2>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-3 border-b space-y-3 shrink-0">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Buscar por nombre..."
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary/30 outline-none"
              />
            </div>
            {/* Upload from PC — one click, opens file picker, uploads to media, auto-selects */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMut.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {uploadMut.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Monitor className="h-4 w-4" />
              )}
              {uploadMut.isPending ? 'Subiendo...' : 'Subir desde PC'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileFromPC}
            />
          </div>

          {/* Category tabs */}
          <div className="flex gap-1.5 flex-wrap">
            {CATEGORIES.map(c => (
              <button
                key={c.key}
                onClick={() => setCategory(c.key)}
                className={cn(
                  'px-3 py-1 text-xs font-medium rounded-full border transition-colors',
                  category === c.key
                    ? 'bg-primary text-white border-primary'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-primary/30'
                )}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {/* File grid */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : filtered.length === 0 ? (
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full py-16 text-center group"
            >
              <Upload className="h-10 w-10 text-slate-200 mx-auto mb-3 group-hover:text-primary/40 transition-colors" />
              <p className="text-sm text-slate-500 group-hover:text-slate-700">No hay archivos{category ? ` en "${CATEGORIES.find(c => c.key === category)?.label}"` : ''}</p>
              <p className="text-xs text-slate-400 mt-1 group-hover:text-primary">Haz click aqui para subir un archivo desde tu PC</p>
            </button>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {/* Upload card — always first in grid */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMut.isPending}
                className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 p-2 hover:border-primary/40 hover:bg-primary/5 transition-all group min-h-[140px]"
              >
                {uploadMut.isPending ? (
                  <Loader2 className="h-8 w-8 text-primary animate-spin mb-2" />
                ) : (
                  <Upload className="h-8 w-8 text-slate-300 group-hover:text-primary/60 mb-2 transition-colors" />
                )}
                <p className="text-[11px] font-medium text-slate-500 group-hover:text-primary">
                  {uploadMut.isPending ? 'Subiendo...' : 'Subir desde PC'}
                </p>
              </button>

              {filtered.map((f: MediaFile) => {
                const isImg = isImage(f)
                const isSelected = selected?.id === f.id
                const fullUrl = mediaFileUrl(f.url)

                return (
                  <button
                    key={f.id}
                    onClick={() => setSelected(isSelected ? null : f)}
                    className={cn(
                      'relative flex flex-col items-center rounded-xl border-2 p-2 transition-all text-left group',
                      isSelected
                        ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                        : 'border-slate-100 hover:border-slate-300 bg-white'
                    )}
                  >
                    <div className="w-full aspect-square rounded-lg overflow-hidden bg-slate-50 flex items-center justify-center mb-2">
                      {isImg ? (
                        <img src={fullUrl} alt={f.original_filename} className="w-full h-full object-cover" />
                      ) : (
                        <FileText className="h-8 w-8 text-slate-300" />
                      )}
                    </div>
                    <p className="text-[11px] font-medium text-slate-800 truncate w-full">{f.original_filename}</p>
                    <div className="flex items-center gap-1.5 w-full mt-0.5">
                      <span className="text-[9px] text-slate-400">{fmtSize(f.file_size)}</span>
                      <span className="text-[9px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">{f.category}</span>
                    </div>
                    {isSelected && (
                      <div className="absolute top-1.5 right-1.5 bg-primary text-white rounded-full p-0.5">
                        <Check className="h-3 w-3" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer: document type + confirm */}
        {selected && (
          <div className="px-6 py-4 border-t bg-slate-50 shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                {isImage(selected) ? (
                  <img src={mediaFileUrl(selected.url)} alt="" className="h-10 w-10 rounded-lg object-cover border shrink-0" />
                ) : (
                  <div className="h-10 w-10 rounded-lg bg-slate-200 flex items-center justify-center shrink-0">
                    <FileText className="h-4 w-4 text-slate-500" />
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{selected.original_filename}</p>
                  <p className="text-[10px] text-slate-400">SHA: {selected.file_hash.slice(0, 12)}...</p>
                </div>
              </div>

              <select
                value={docType}
                onChange={e => setDocType(e.target.value as EvidenceDocumentType)}
                className="text-sm border border-slate-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-primary/20"
              >
                {DOC_TYPES.map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>

              <input
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Descripcion (opcional)"
                className="text-sm border border-slate-200 rounded-lg px-3 py-2 w-40 outline-none focus:ring-2 focus:ring-primary/20"
              />

              <button
                onClick={handleConfirm}
                disabled={linking}
                className="inline-flex items-center gap-1.5 px-5 py-2 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors shrink-0"
              >
                {linking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Vincular
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
