import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useCreateAsset } from '@/hooks/useAssets'
import { useToast } from '@/store/toast'
import { tryParseJson } from '@/lib/utils'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input, Textarea } from '@/components/ui/Input'

const schema = z.object({
  asset_mint:               z.string().min(1, 'Requerido').max(64),
  product_type:             z.string().min(1, 'Requerido').max(100),
  initial_custodian_wallet: z.string().min(1, 'Requerido'),
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

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { asset_mint: '', product_type: '', initial_custodian_wallet: '', metadata_raw: '' },
  })

  const onSubmit = async (data: FormData) => {
    try {
      const res = await createAsset.mutateAsync({
        asset_mint:               data.asset_mint.trim(),
        product_type:             data.product_type.trim(),
        initial_custodian_wallet: data.initial_custodian_wallet.trim(),
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
