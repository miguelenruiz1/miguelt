import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { KeyRound } from 'lucide-react'
import { useGenerateWallet } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useToast } from '@/store/toast'
import { parseTags } from '@/lib/utils'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import type { WalletStatus } from '@/types/api'

const schema = z.object({
  name:             z.string().optional(),
  organization_id:  z.string().optional(),
  extra_tags:       z.string(),
  status:           z.enum(['active', 'suspended', 'revoked']),
})

type FormData = z.infer<typeof schema>

interface Props { open: boolean; onClose: () => void; preSelectedOrgId?: string }

export function GenerateWalletModal({ open, onClose, preSelectedOrgId }: Props) {
  const generateWallet = useGenerateWallet()
  const toast = useToast()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', organization_id: preSelectedOrgId ?? '', extra_tags: '', status: 'active' },
  })

  useEffect(() => {
    if (open) reset({ name: '', organization_id: preSelectedOrgId ?? '', extra_tags: '', status: 'active' })
  }, [open, preSelectedOrgId, reset])

  const orgOptions = [
    { label: '— Sin organización —', value: '' },
    ...orgs.map((o) => ({ label: o.name, value: o.id })),
  ]

  const onSubmit = async (data: FormData) => {
    const tags = parseTags(data.extra_tags)
    try {
      await generateWallet.mutateAsync({
        tags,
        status: data.status as WalletStatus,
        name: data.name?.trim() || undefined,
        organization_id: data.organization_id || undefined,
      })
      toast.success('Wallet de custodio creada exitosamente')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al crear wallet'
      toast.error(msg)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Crear Wallet de Custodio"
      description="Genera un nuevo par de llaves Solana para un custodio logístico"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>
            <KeyRound className="h-4 w-4" /> Crear Wallet
          </Button>
        </>
      }
    >
      <div className="mb-4 flex gap-3 rounded-xl bg-primary/10 border border-primary/20 px-4 py-3">
        <KeyRound className="h-4 w-4 text-primary shrink-0 mt-0.5" />
        <p className="text-xs text-primary">
          El sistema genera un nuevo par de llaves Solana. La llave pública se registra
          en la lista de permitidos y la wallet puede recibir activos inmediatamente.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <Input
          label="Nombre de Wallet"
          placeholder="Ej: Almacén Norte — Principal"
          hint="Etiqueta para identificar esta wallet."
          {...register('name')}
        />
        <Select
          label="Organización"
          options={orgOptions}
          hint="Vincular wallet a una organización."
          {...register('organization_id')}
        />
        <Input
          label="Etiquetas Adicionales"
          placeholder="bodega-norte, ruta-01  (separadas por coma)"
          hint="Opcional. Útil para filtrar activos por ubicación o ruta."
          {...register('extra_tags')}
        />
        <Select
          label="Estado Inicial"
          options={[
            { value: 'active',    label: 'Activa' },
            { value: 'suspended', label: 'Suspendida' },
          ]}
          {...register('status')}
        />
      </form>
    </Dialog>
  )
}
