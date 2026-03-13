/**
 * All custody-event action modals in one file:
 *  HandoffModal, ArrivedModal, LoadedModal, QCModal, ReleaseModal
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AlertTriangle } from 'lucide-react'
import { useHandoff, useArrived, useLoaded, useQC, useRelease, useBurn } from '@/hooks/useAssets'
import { ApiError } from '@/lib/api'
import { useAdminStore } from '@/store/admin'
import { useToast } from '@/store/toast'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input, Select, Textarea } from '@/components/ui/Input'
import { shortPubkey } from '@/lib/utils'
import type { Asset } from '@/types/api'

// ─── Handoff ─────────────────────────────────────────────────────────────────

const handoffSchema = z.object({
  to_wallet: z.string().min(1, 'Required'),
  location_label: z.string().optional(),
  notes: z.string().optional(),
})

type HandoffForm = z.infer<typeof handoffSchema>

export function HandoffModal({ asset, open, onClose }: { asset: Asset; open: boolean; onClose: () => void }) {
  const handoff = useHandoff(asset.id)
  const toast = useToast()
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<HandoffForm>({
    resolver: zodResolver(handoffSchema),
  })

  const onSubmit = async (data: HandoffForm) => {
    try {
      await handoff.mutateAsync({
        to_wallet: data.to_wallet.trim(),
        location: data.location_label ? { label: data.location_label } : undefined,
        data: data.notes ? { notes: data.notes } : {},
      })
      toast.success('Transferencia registrada')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Error en la transferencia'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Transferir Carga" description={`Transferir custodia desde ${shortPubkey(asset.current_custodian_wallet)}`} size="sm"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Confirmar Transferencia</Button></>}
    >
      <form className="flex flex-col gap-4">
        <Input label="Custodio destino *" placeholder="Wallet del custodio receptor (debe estar activo)" error={errors.to_wallet?.message} {...register('to_wallet')} />
        <Input label="Ubicación" placeholder="Ej: Aeropuerto CDMX Puerta 3" {...register('location_label')} />
        <Input label="Notas" placeholder="Opcional" {...register('notes')} />
      </form>
    </Dialog>
  )
}

// ─── Arrived ─────────────────────────────────────────────────────────────────

const arrivedSchema = z.object({
  label: z.string().optional(),
  notes: z.string().optional(),
})

type ArrivedForm = z.infer<typeof arrivedSchema>

export function ArrivedModal({ asset, open, onClose }: { asset: Asset; open: boolean; onClose: () => void }) {
  const arrived = useArrived(asset.id)
  const toast = useToast()
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<ArrivedForm>({
    resolver: zodResolver(arrivedSchema),
  })

  const onSubmit = async (data: ArrivedForm) => {
    try {
      await arrived.mutateAsync({
        location: data.label ? { label: data.label } : undefined,
        data: data.notes ? { notes: data.notes } : {},
      })
      toast.success('Llegada registrada')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Error al registrar llegada'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Registrar Llegada" description="Confirma que la carga llegó al destino del custodio actual" size="sm"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Confirmar Llegada</Button></>}
    >
      <form className="flex flex-col gap-4">
        <Input label="Ubicación" placeholder="Ej: Bodega A, Bahía 5" {...register('label')} />
        <Input label="Notas" {...register('notes')} />
      </form>
    </Dialog>
  )
}

// ─── Loaded ───────────────────────────────────────────────────────────────────

const loadedSchema = z.object({
  batch: z.string().optional(),
  notes: z.string().optional(),
})

type LoadedForm = z.infer<typeof loadedSchema>

export function LoadedModal({ asset, open, onClose }: { asset: Asset; open: boolean; onClose: () => void }) {
  const loaded = useLoaded(asset.id)
  const toast = useToast()
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<LoadedForm>({
    resolver: zodResolver(loadedSchema),
  })

  const onSubmit = async (data: LoadedForm) => {
    try {
      await loaded.mutateAsync({ data: { batch: data.batch, notes: data.notes } })
      toast.success('Carga en transporte registrada')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Error al registrar carga'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Registrar Carga en Transporte" description="La carga ha sido subida al vehículo de transporte" size="sm"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Confirmar</Button></>}
    >
      <form className="flex flex-col gap-4">
        <Input label="Lote / Contenedor" placeholder="Ej: LOTE-2026-001" {...register('batch')} />
        <Input label="Notas" {...register('notes')} />
      </form>
    </Dialog>
  )
}

// ─── QC ───────────────────────────────────────────────────────────────────────

const qcSchema = z.object({
  result: z.enum(['pass', 'fail']),
  notes: z.string().optional(),
})

type QCForm = z.infer<typeof qcSchema>

export function QCModal({ asset, open, onClose }: { asset: Asset; open: boolean; onClose: () => void }) {
  const qc = useQC(asset.id)
  const toast = useToast()
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<QCForm>({
    resolver: zodResolver(qcSchema),
    defaultValues: { result: 'pass' },
  })

  const onSubmit = async (data: QCForm) => {
    try {
      await qc.mutateAsync({ result: data.result, notes: data.notes })
      toast.success(`QC ${data.result === 'pass' ? 'aprobado' : 'rechazado'} registrado`)
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Error en control de calidad'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Control de Calidad" description="Registrar resultado de la inspección de calidad" size="sm"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Registrar QC</Button></>}
    >
      <form className="flex flex-col gap-4">
        <Select label="Resultado *" options={[{ value: 'pass', label: '✅ Aprobado' }, { value: 'fail', label: '❌ Rechazado' }]} {...register('result')} />
        <Textarea label="Notas" placeholder="Observaciones del inspector, resultados del checklist..." {...register('notes')} />
      </form>
    </Dialog>
  )
}

// ─── Release ──────────────────────────────────────────────────────────────────

const releaseSchema = z.object({
  external_wallet: z.string().min(1, 'Required'),
  reason: z.string().min(1, 'Required'),
})

type ReleaseForm = z.infer<typeof releaseSchema>

export function ReleaseModal({ asset, open, onClose }: { asset: Asset; open: boolean; onClose: () => void }) {
  const release = useRelease(asset.id)
  const toast = useToast()
  const { adminKey } = useAdminStore()

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ReleaseForm>({
    resolver: zodResolver(releaseSchema),
  })

  const onSubmit = async (data: ReleaseForm) => {
    if (!adminKey) { toast.error('Configura tu Clave Admin primero (botón superior derecho)'); return }
    try {
      await release.mutateAsync({ data: { external_wallet: data.external_wallet, reason: data.reason }, adminKey })
      toast.success('Carga liberada')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Error al liberar la carga'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Liberar Carga" description="Liberar la carga fuera de la cadena de custodia" size="sm"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button variant="danger" loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Liberar</Button></>}
    >
      {/* Warning */}
      <div className="mb-5 flex gap-3 rounded-lg bg-amber-50 border border-amber-200 p-3">
        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-700">
          Esta acción es <strong>irreversible</strong>. La carga saldrá de la cadena de custodia.
          Requiere clave de administrador.
        </p>
      </div>

      {!adminKey && (
        <p className="mb-4 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          No hay clave de administrador configurada. Configúrala en Plataforma → Blockchain.
        </p>
      )}

      <form className="flex flex-col gap-4">
        <Input label="Wallet externo *" placeholder="Wallet del destinatario (puede estar fuera del allowlist)" error={errors.external_wallet?.message} {...register('external_wallet')} />
        <Textarea label="Razón *" placeholder="Ej: Venta completada — Orden #OC-2026-0891" error={errors.reason?.message} rows={2} {...register('reason')} />
      </form>
    </Dialog>
  )
}

// ─── Completar Entrega ──────────────────────────────────────────────────────

const burnSchema = z.object({
  reason: z.string().min(1, 'Requerido'),
})

type BurnForm = z.infer<typeof burnSchema>

export function BurnModal({ asset, open, onClose }: { asset: Asset; open: boolean; onClose: () => void }) {
  const burn = useBurn(asset.id)
  const toast = useToast()

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<BurnForm>({
    resolver: zodResolver(burnSchema),
  })

  const onSubmit = async (data: BurnForm) => {
    try {
      await burn.mutateAsync({ reason: data.reason })
      toast.success('Entrega completada — carga finalizada')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Error al completar la entrega'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Completar Entrega" description="Finalizar la cadena de custodia de esta carga" size="sm"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Completar Entrega</Button></>}
    >
      {/* Info */}
      <div className="mb-5 flex gap-3 rounded-lg bg-cyan-50 border border-cyan-200 p-3">
        <AlertTriangle className="h-4 w-4 text-cyan-600 shrink-0 mt-0.5" />
        <p className="text-xs text-cyan-700">
          La carga será marcada como <strong>entregada</strong> y se cerrará permanentemente su cadena de custodia.
          Todos los eventos quedarán certificados en blockchain como registro inmutable.
        </p>
      </div>

      <form className="flex flex-col gap-4">
        <Textarea label="Observaciones de entrega *" placeholder="Ej: Entregado al destinatario final en bodega central" error={errors.reason?.message} rows={2} {...register('reason')} />
      </form>
    </Dialog>
  )
}
