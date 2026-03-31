import { useState } from 'react'
import { FileText, Plus, Trash2, ExternalLink, FileImage, FolderOpen } from 'lucide-react'
import { cn } from '@/lib/utils'
import { mediaFileUrl } from '@/lib/media-api'
import MediaPickerModal from '@/components/compliance/MediaPickerModal'
import type { DocumentLink, DocumentLinkInput, EvidenceDocumentType } from '@/types/compliance'

const DOC_TYPE_LABELS: Record<string, string> = {
  land_title: 'Titulo de tierra',
  legal_cert: 'Certificado legal',
  deforestation_report: 'Reporte de deforestacion',
  satellite_image: 'Imagen satelital',
  supplier_declaration: 'Declaracion de proveedor',
  transport_doc: 'Documento de transporte',
  geojson_boundary: 'Poligono GeoJSON',
  other: 'Otro',
}

const DOC_TYPE_COLORS: Record<string, string> = {
  land_title: 'bg-amber-50 text-amber-700 border-amber-200',
  legal_cert: 'bg-blue-50 text-blue-700 border-blue-200',
  deforestation_report: 'bg-green-50 text-green-700 border-green-200',
  satellite_image: 'bg-purple-50 text-purple-700 border-purple-200',
  supplier_declaration: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  transport_doc: 'bg-orange-50 text-orange-700 border-orange-200',
  geojson_boundary: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  other: 'bg-slate-50 text-slate-600 border-slate-200',
}

interface Props {
  documents: DocumentLink[]
  isLoading: boolean
  onAttach: (data: DocumentLinkInput) => Promise<void>
  onDetach: (docId: string) => Promise<void>
  isPending?: boolean
}

export default function DocumentUploader({ documents, isLoading, onAttach, onDetach, isPending }: Props) {
  const [showPicker, setShowPicker] = useState(false)

  const alreadyLinkedIds = documents.map(d => d.media_file_id)

  async function handleSelect(mediaFileId: string, documentType: EvidenceDocumentType, description?: string) {
    await onAttach({ media_file_id: mediaFileId, document_type: documentType, description })
  }

  if (isLoading) {
    return <div className="text-sm text-slate-400 py-6 text-center">Cargando documentos...</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-700">Documentos de evidencia</p>
          <p className="text-xs text-slate-500">{documents.length} documento{documents.length !== 1 ? 's' : ''} adjunto{documents.length !== 1 ? 's' : ''}</p>
        </div>
        <button onClick={() => setShowPicker(true)}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors">
          <FolderOpen className="h-3.5 w-3.5" /> Adjuntar desde Media
        </button>
      </div>

      {/* Document list */}
      {documents.length === 0 ? (
        <button
          onClick={() => setShowPicker(true)}
          className="w-full rounded-xl border-2 border-dashed border-slate-200 p-8 text-center hover:border-primary/30 hover:bg-primary/5 transition-colors group"
        >
          <FolderOpen className="h-8 w-8 text-slate-200 mx-auto mb-2 group-hover:text-primary/40" />
          <p className="text-sm font-medium text-slate-600 mb-1">Sin documentos adjuntos</p>
          <p className="text-xs text-slate-400">Haz click para abrir la biblioteca de media y seleccionar o subir archivos</p>
        </button>
      ) : (
        <div className="space-y-2">
          {documents.map(doc => {
            const isImg = doc.filename?.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i) || doc.document_type === 'satellite_image'
            const fullUrl = doc.url ? mediaFileUrl(doc.url) : null

            return (
              <div key={doc.id} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3">
                {/* Thumbnail or icon */}
                {isImg && fullUrl ? (
                  <a href={fullUrl} target="_blank" rel="noopener noreferrer" className="shrink-0">
                    <img
                      src={fullUrl}
                      alt={doc.filename ?? 'preview'}
                      className="h-10 w-10 rounded-lg object-cover border border-slate-200 hover:ring-2 hover:ring-primary/30 transition-all"
                    />
                  </a>
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-50 shrink-0">
                    {isImg ? <FileImage className="h-4 w-4 text-purple-400" /> : <FileText className="h-4 w-4 text-slate-400" />}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{doc.filename ?? 'Archivo'}</p>
                  {doc.description && <p className="text-xs text-slate-500 truncate">{doc.description}</p>}
                </div>
                <span className={cn(
                  'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0',
                  DOC_TYPE_COLORS[doc.document_type] ?? DOC_TYPE_COLORS.other,
                )}>
                  {DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}
                </span>
                {doc.file_hash && (
                  <span className="text-[10px] font-mono text-slate-400 shrink-0" title={doc.file_hash}>
                    SHA: {doc.file_hash.slice(0, 8)}
                  </span>
                )}
                {fullUrl && (
                  <a href={fullUrl} target="_blank" rel="noopener noreferrer"
                    className="rounded-lg p-1.5 text-slate-400 hover:text-primary hover:bg-primary/10 transition-colors">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
                <button onClick={() => onDetach(doc.id)} disabled={isPending}
                  className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Media Picker Modal */}
      <MediaPickerModal
        open={showPicker}
        onClose={() => setShowPicker(false)}
        onSelect={handleSelect}
        excludeIds={alreadyLinkedIds}
      />
    </div>
  )
}
