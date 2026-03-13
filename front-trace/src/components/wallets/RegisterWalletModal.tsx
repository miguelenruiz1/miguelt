import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRegisterWallet } from '@/hooks/useWallets'
import { useCustodianTypes, useOrganizations } from '@/hooks/useTaxonomy'
import { useToast } from '@/store/toast'
import { parseTags } from '@/lib/utils'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import type { WalletStatus } from '@/types/api'

const schema = z.object({
  wallet_pubkey:   z.string().min(8, 'Llave pública muy corta').max(64),
  name:            z.string().optional(),
  custodian_type:  z.string().optional(),
  organization_id: z.string().optional(),
  tags:            z.string(),
  status:          z.enum(['active', 'suspended', 'revoked']),
})

type FormData = z.infer<typeof schema>

interface Props { open: boolean; onClose: () => void }

export function RegisterWalletModal({ open, onClose }: Props) {
  const register_ = useRegisterWallet()
  const toast = useToast()
  const { data: custodianTypes = [] } = useCustodianTypes()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []

  const { register, handleSubmit, reset, watch, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { wallet_pubkey: '', name: '', custodian_type: '', organization_id: '', tags: '', status: 'active' },
  })

  const selectedTypeId = watch('custodian_type')
  const filteredOrgs = selectedTypeId
    ? orgs.filter((o) => o.custodian_type_id === selectedTypeId)
    : orgs

  const typeOptions = [
    { label: '— Sin tipo —', value: '' },
    ...custodianTypes.map((t) => ({ label: t.name, value: t.id })),
  ]

  const orgOptions = [
    { label: '— Sin organización —', value: '' },
    ...filteredOrgs.map((o) => ({ label: o.name, value: o.id })),
  ]

  const onSubmit = async (data: FormData) => {
    const selectedType = custodianTypes.find((t) => t.id === data.custodian_type)
    const allTags = [
      ...(selectedType ? [selectedType.slug] : []),
      ...parseTags(data.tags),
    ]
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
          placeholder="Ej: Almacen-Norte-CDMX o dirección Solana"
          error={errors.wallet_pubkey?.message}
          {...register('wallet_pubkey')}
        />
        <Input
          label="Nombre de Wallet"
          placeholder="Ej: Almacén Norte — Principal"
          hint="Etiqueta opcional para identificar la wallet."
          {...register('name')}
        />
        <Select
          label="Tipo de Custodio"
          options={typeOptions}
          {...register('custodian_type')}
        />
        <Select
          label="Organización"
          options={orgOptions}
          hint="Opcional. Vincular a una organización."
          {...register('organization_id')}
        />
        <Input
          label="Etiquetas Adicionales"
          placeholder="almacen, proveedor, transportista  (separadas por coma)"
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
