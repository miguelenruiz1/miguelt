/**
 * Generic workflow-driven event modal.
 * Adapts its form fields based on WorkflowEventType config.
 * Always shows wallet selector (required or optional) for traceability.
 * Includes document upload zones based on event type requirements.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRecordEvent } from '@/hooks/useAssets'
import { useWalletList } from '@/hooks/useWallets'
import { useDocumentRequirements } from '@/hooks/useDocuments'
import { api, ApiError } from '@/lib/api'
import { useToast } from '@/store/toast'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { Button } from '@/components/ui/button'
import { Input, Select, Textarea } from '@/components/ui/input'
import { shortPubkey } from '@/lib/utils'
import { resolveIcon, colorStyle } from '@/lib/icon-map'
import { Upload, X, FileText, Image, CheckCircle2, AlertTriangle } from 'lucide-react'
import type { Asset, AvailableAction, DocumentRequirement } from '@/types/api'

function buildSchema(action: AvailableAction) {
  const et = action.event_type
  const fields: Record<string, z.ZodTypeAny> = {}

  // Wallet: required if event_type says so, optional otherwise
  if (et?.requires_wallet) {
    fields.to_wallet = z.string().min(1, 'Selecciona un custodio')
  } else {
    fields.to_wallet = z.string().optional()
  }

  if (et?.requires_reason) {
    fields.reason = z.string().min(1, 'La razón es obligatoria')
  }

  // QC needs result selector
  if (action.event_type_slug === 'QC') {
    fields.result = z.enum(['pass', 'fail'], { required_error: 'Selecciona el resultado' })
  }

  fields.location_label = z.string().optional()
  fields.notes = z.string().optional()

  return z.object(fields)
}

type FormData = Record<string, string | undefined>

interface Props {
  asset: Asset
  action: AvailableAction
  open: boolean
  onClose: () => void
}

// Staged file per document type
type StagedFiles = Record<string, File[]>

export function WorkflowEventModal({ asset, action, open, onClose }: Props) {
  const et = action.event_type
  const walletRequired = et?.requires_wallet ?? false
  const schema = buildSchema(action)
  const recordEvent = useRecordEvent(asset.id)
  const toast = useToast()
  const [stagedFiles, setStagedFiles] = useState<StagedFiles>({})
  const [uploading, setUploading] = useState(false)

  // Load document requirements
  const eventTypeSlug = action.event_type_slug || ''
  const { data: docReqs } = useDocumentRequirements(asset.id, eventTypeSlug)
  const requirements = docReqs?.merged_requirements ?? []

  // Always load wallets — essential for traceability
  const { data: walletsData } = useWalletList({ status: 'active', limit: 200 })
  const wallets = (walletsData?.items ?? []).filter(
    w => w.wallet_pubkey !== asset.current_custodian_wallet
  )

  const currentCustodianName = walletsData?.items?.find(
    w => w.wallet_pubkey === asset.current_custodian_wallet
  )?.name || shortPubkey(asset.current_custodian_wallet, 6)

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  // Reset form when modal opens with a new action
  useEffect(() => {
    if (open) {
      reset()
      setStagedFiles({})
    }
  }, [open, action.transition_id, reset])

  const addFiles = useCallback((docType: string, files: FileList | null) => {
    if (!files?.length) return
    setStagedFiles(prev => ({
      ...prev,
      [docType]: [...(prev[docType] ?? []), ...Array.from(files)],
    }))
  }, [])

  const removeFile = useCallback((docType: string, index: number) => {
    setStagedFiles(prev => ({
      ...prev,
      [docType]: (prev[docType] ?? []).filter((_, i) => i !== index),
    }))
  }, [])

  const onSubmit = async (data: FormData) => {
    try {
      const eventType = action.event_type_slug
        || action.label?.toUpperCase().replace(/\s+/g, '_')
        || 'TRANSITION'

      // 1. Create the event
      const resp = await recordEvent.mutateAsync({
        event_type: eventType,
        to_wallet: data.to_wallet?.trim() || undefined,
        location: data.location_label ? { label: data.location_label } : undefined,
        notes: data.notes || undefined,
        reason: data.reason || undefined,
        result: data.result || undefined,
        data: {},
      })

      // 2. Upload staged documents to the created event
      const eventId = (resp as { event?: { id?: string } })?.event?.id
      if (eventId) {
        const entries = Object.entries(stagedFiles).filter(([, files]) => files.length > 0)
        if (entries.length > 0) {
          setUploading(true)
          for (const [docType, files] of entries) {
            const req = requirements.find(r => r.type === docType)
            try {
              await api.documents.upload(asset.id, eventId, files, docType, req?.label)
            } catch (uploadErr) {
              const uploadMsg = uploadErr instanceof ApiError ? uploadErr.detail : 'Error desconocido'
              toast.error(`Error subiendo ${req?.label ?? docType}: ${uploadMsg}`)
            }
          }
          setUploading(false)
        }
      }

      const label = et?.name || action.label || action.event_type_slug
      toast.success(`${label} registrado`)
      reset()
      setStagedFiles({})
      onClose()
    } catch (err: unknown) {
      setUploading(false)
      const msg = err instanceof ApiError
        ? err.message
        : err instanceof Error ? err.message : 'Error al registrar evento'
      toast.error(msg)
    }
  }

  const Icon = resolveIcon(et?.icon || action.to_state?.icon)
  const title = et?.name || action.label || action.event_type_slug || 'Evento'
  const toStateLabel = action.to_state?.label

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={toStateLabel ? `${currentCustodianName} → ${toStateLabel}` : undefined}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button loading={isSubmitting || uploading} onClick={handleSubmit(onSubmit)}>
            {uploading ? 'Subiendo docs...' : 'Confirmar'}
          </Button>
        </>
      }
    >
      <form className="flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl border"
            style={colorStyle(et?.color || action.to_state?.color || '#6366f1')}
          >
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800">{title}</p>
            {et?.description && (
              <p className="text-xs text-slate-500">{et.description}</p>
            )}
          </div>
          {action.to_state && (
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full border"
              style={colorStyle(action.to_state.color)}
            >
              → {action.to_state.label}
            </span>
          )}
        </div>

        {/* Current custodian info */}
        <div className="bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
          <p className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider">Custodio actual</p>
          <p className="text-xs font-medium text-slate-700">{currentCustodianName}</p>
        </div>

        {/* Wallet selector — always visible for traceability */}
        <Select
          label={walletRequired ? 'Nuevo custodio *' : 'Transferir a custodio (opcional)'}
          error={(errors as Record<string, { message?: string }>).to_wallet?.message}
          options={[
            { label: walletRequired ? 'Seleccionar custodio...' : '— Mantener custodio actual —', value: '' },
            ...wallets.map(w => ({
              label: `${w.name || shortPubkey(w.wallet_pubkey)}`,
              value: w.wallet_pubkey,
            })),
          ]}
          {...register('to_wallet')}
        />
        {wallets.length === 0 && (
          <p className="text-xs text-amber-600 -mt-2">No hay otros custodios activos.</p>
        )}

        {/* QC result selector */}
        {action.event_type_slug === 'QC' && (
          <Select
            label="Resultado *"
            error={(errors as Record<string, { message?: string }>).result?.message}
            options={[
              { label: 'Seleccionar resultado...', value: '' },
              { label: 'Aprobado (Pass)', value: 'pass' },
              { label: 'Rechazado (Fail)', value: 'fail' },
            ]}
            {...register('result')}
          />
        )}

        {/* Reason (required) */}
        {et?.requires_reason && (
          <Textarea
            label="Razón *"
            placeholder="Motivo del evento..."
            error={(errors as Record<string, { message?: string }>).reason?.message}
            {...register('reason')}
          />
        )}

        {/* Location */}
        <Input
          label="Ubicación"
          placeholder="Ej: Bodega A, Bahía 5"
          {...register('location_label')}
        />

        {/* Notes */}
        <Textarea
          label={et?.requires_notes ? 'Notas *' : 'Notas'}
          placeholder="Información adicional..."
          {...register('notes')}
        />

        {/* Document uploads */}
        {requirements.length > 0 && (
          <div className="border-t border-slate-100 pt-3 mt-1">
            <p className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              Documentación
              {docReqs?.compliance_active && (
                <span className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded-full border border-amber-200 font-medium">
                  EUDR
                </span>
              )}
            </p>
            <div className="flex flex-col gap-2.5">
              {requirements.map((req) => (
                <DocumentDropZone
                  key={req.type}
                  requirement={req}
                  files={stagedFiles[req.type] ?? []}
                  onAdd={(files) => addFiles(req.type, files)}
                  onRemove={(idx) => removeFile(req.type, idx)}
                  isCompliance={docReqs?.compliance_requirements?.some(r => r.type === req.type) ?? false}
                />
              ))}
            </div>
          </div>
        )}
      </form>
    </Dialog>
  )
}


// ─── Document Drop Zone ──────────────────────────────────────────────────────

function DocumentDropZone({
  requirement,
  files,
  onAdd,
  onRemove,
  isCompliance,
}: {
  requirement: DocumentRequirement
  files: File[]
  onAdd: (files: FileList | null) => void
  onRemove: (idx: number) => void
  isCompliance: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const maxCount = requirement.max_count ?? 1
  const canAdd = files.length < maxCount

  const acceptStr = requirement.accept?.join(',') ?? '*'

  const isImage = (f: File) => f.type.startsWith('image/')
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
  }

  return (
    <div className={`rounded-lg border p-2.5 ${
      requirement.required
        ? files.length > 0
          ? 'border-emerald-200 bg-emerald-50/30'
          : 'border-amber-200 bg-amber-50/30'
        : 'border-slate-200 bg-slate-50/30'
    }`}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-slate-700">{requirement.label}</span>
          {requirement.required && (
            <span className="text-[9px] font-bold text-amber-600">*</span>
          )}
          {isCompliance && (
            <span className="text-[9px] px-1 py-0.5 bg-indigo-50 text-indigo-600 rounded border border-indigo-200 font-medium">
              EUDR
            </span>
          )}
        </div>
        {files.length > 0 && (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        )}
      </div>

      {/* Staged files */}
      {files.length > 0 && (
        <div className="flex flex-col gap-1 mb-1.5">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs bg-white rounded px-2 py-1 border border-slate-100">
              {isImage(f) ? (
                <Image className="h-3 w-3 text-slate-400 shrink-0" />
              ) : (
                <FileText className="h-3 w-3 text-slate-400 shrink-0" />
              )}
              <span className="truncate flex-1 text-slate-600">{f.name}</span>
              <span className="text-slate-400 shrink-0">{formatSize(f.size)}</span>
              <button
                type="button"
                onClick={() => onRemove(i)}
                className="text-slate-400 hover:text-red-500 shrink-0"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload button */}
      {canAdd && (
        <>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept={acceptStr}
            multiple={maxCount > 1}
            onChange={(e) => {
              onAdd(e.target.files)
              if (inputRef.current) inputRef.current.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="w-full flex items-center justify-center gap-1.5 rounded border border-dashed border-slate-300 py-1.5 text-xs text-slate-500 hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/30 transition-colors"
          >
            <Upload className="h-3 w-3" />
            {files.length === 0 ? 'Seleccionar archivo' : 'Agregar otro'}
          </button>
        </>
      )}

      {/* Missing warning */}
      {requirement.required && files.length === 0 && (
        <div className="flex items-center gap-1 mt-1">
          <AlertTriangle className="h-3 w-3 text-amber-500" />
          <span className="text-[10px] text-amber-600">Requerido{isCompliance ? ' por normativa EUDR' : ''}</span>
        </div>
      )}
    </div>
  )
}
