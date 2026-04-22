import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRegisterWallet } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useToast } from '@/store/toast'
import { parseTags } from '@/lib/utils'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import type { WalletStatus } from '@/types/api'

const schema = z.object({
  wallet_pubkey:   z.string().min(8, 'Llave pública muy corta').max(64),
  name:            z.string().optional(),
  organization_id: z.string().optional(),
  tags:            z.string(),
  status:          z.enum(['active', 'suspended', 'revoked']),
})

type FormData = z.infer<typeof schema>

interface Props { open: boolean; onClose: () => void }

export function RegisterWalletModal({ open, onClose }: Props) {
  const register_ = useRegisterWallet()
  const toast = useToast()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { wallet_pubkey: '', name: '', organization_id: '', tags: '', status: 'active' },
  })

  const orgOptions = [
    { label: '— Sin organización —', value: '' },
    ...orgs.map((o) => ({ label: o.name, value: o.id })),
  ]

  const onSubmit = async (data: FormData) => {
    const allTags = parseTags(data.tags)
    try {
      await register_.mutateAsync({
        wallet_pubkey:   data.wallet_pubkey.trim(),
        tags:            allTags,
        status:          data.status as WalletStatus,
        name:            data.name?.trim() || undefined,
        organization_id: data.organization_id || undefined,
      })
      toast.success('Wallet registrada exitosamente')
      reset()
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al registrar wallet'
      toast.error(msg)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Registrar Wallet"
      description="Agrega una wallet externa a la lista de permitidos"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button loading={isSubmitting} onClick={handleSubmit(onSubmit)}>Registrar</Button>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <Input
          label="Llave Pública *"
          placeholder="Ej: dirección Solana o identificador externo"
          error={errors.wallet_pubkey?.message}
          {...register('wallet_pubkey')}
        />
        <Input
          label="Nombre de Wallet"
          placeholder="Ej: Almacén Norte — Principal"
          hint="Etiqueta para identificar la wallet."
          {...register('name')}
        />
        <Select
          label="Organización"
          options={orgOptions}
          hint="Vincular a una organización."
          {...register('organization_id')}
        />
        <Input
          label="Etiquetas Adicionales"
          placeholder="bodega, ruta-norte  (separadas por coma)"
          hint="Opcional. Usadas para filtrar."
          {...register('tags')}
        />
        <Select
          label="Estado Inicial"
          options={[
            { value: 'active',    label: 'Activa' },
            { value: 'suspended', label: 'Suspendida' },
            { value: 'revoked',   label: 'Revocada' },
          ]}
          {...register('status')}
        />
      </form>
    </Dialog>
  )
}
