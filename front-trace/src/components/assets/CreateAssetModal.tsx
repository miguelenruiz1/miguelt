import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useCreateAsset } from '@/hooks/useAssets'
import { usePlots } from '@/hooks/useCompliance'
import { useToast } from '@/store/toast'
import { tryParseJson } from '@/lib/utils'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/input'

const schema = z.object({
  asset_mint:               z.string().min(1, 'Requerido').max(64),
  product_type:             z.string().min(1, 'Requerido').max(100),
  initial_custodian_wallet: z.string().min(1, 'Requerido'),
  plot_id:                  z.string().optional(),
  metadata_raw:             z.string().refine(
    (s) => s === '' || tryParseJson(s) !== null,
    { message: 'Debe ser JSON válido o vacío' },
  ),
})

type FormData = z.infer<typeof schema>

interface Props { open: boolean; onClose: () => void }

export function CreateAssetModal({ open, onClose }: Props) {
  const createAsset = useCreateAsset()
  const toast       = useToast()
  const navigate    = useNavigate()
  const { data: plots } = usePlots({ is_active: true })

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { asset_mint: '', product_type: '', initial_custodian_wallet: '', plot_id: '', metadata_raw: '' },
  })

  const onSubmit = async (data: FormData) => {
    try {
      const res = await createAsset.mutateAsync({
        asset_mint:               data.asset_mint.trim(),
        product_type:             data.product_type.trim(),
        initial_custodian_wallet: data.initial_custodian_wallet.trim(),
        ...(data.plot_id ? { plot_id: data.plot_id } : {}),
        metadata: data.metadata_raw ? (tryParseJson(data.metadata_raw) ?? {}) : {},
      })
      toast.success('Carga registrada exitosamente')
      reset()
      onClose()
      navigate(`/assets/${res.asset.id}`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al registrar la carga'
      toast.error(msg)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Registrar Carga Existente"
      description="Registra una carga que ya tiene un identificador asignado"
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Registrar Carga</Button>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <Input
          label="Identificador de la carga *"
          placeholder="Código único o dirección blockchain"
          error={errors.asset_mint?.message}
          {...register('asset_mint')}
        />
        <Input
          label="Tipo de producto *"
          placeholder="café, arroz, cacao, electrónicos..."
          error={errors.product_type?.message}
          {...register('product_type')}
        />
        <Input
          label="Custodio inicial *"
          placeholder="Wallet del custodio (debe estar en el allowlist)"
          error={errors.initial_custodian_wallet?.message}
          {...register('initial_custodian_wallet')}
        />
        <div>
          <label className="text-xs font-medium text-foreground block mb-1.5">
            Parcela de origen (opcional)
          </label>
          <select
            className="w-full rounded-lg border border-slate-300 bg-card px-3 py-2 text-sm text-foreground hover:border-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 transition-colors"
            {...register('plot_id')}
          >
            <option value="">— Sin parcela —</option>
            {(plots ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {`${p.plot_code ?? p.id.slice(0, 8)} — ${p.commodity_type ?? 'sin commodity'} — ${p.region ?? '-'}`}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-muted-foreground mt-1">
            Vincula la carga a una parcela EUDR para trazabilidad finca → lote.
          </p>
        </div>
        <Textarea
          label="Metadatos (JSON)"
          placeholder={'{\n  "peso": 1000,\n  "unidad": "kg",\n  "origen": "Huila"\n}'}
          error={errors.metadata_raw?.message}
          hint="Opcional. Cualquier objeto JSON con información adicional."
          rows={4}
          {...register('metadata_raw')}
        />
      </form>
    </Dialog>
  )
}
