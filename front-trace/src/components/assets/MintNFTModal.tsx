import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useMintAsset } from '@/hooks/useAssets'
import { useOrganizations, useOrgWallets } from '@/hooks/useTaxonomy'
import { useWalletList } from '@/hooks/useWallets'
import { useToast } from '@/store/toast'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// ─── Product type catalog ──────────────────────────────────────────────────────

const PRODUCT_TYPES = [
  { value: 'cafe',     label: 'Café',          emoji: '☕' },
  { value: 'arroz',   label: 'Arroz',          emoji: '🌾' },
  { value: 'maiz',    label: 'Maíz',           emoji: '🌽' },
  { value: 'cacao',   label: 'Cacao',          emoji: '🍫' },
  { value: 'caña',    label: 'Caña de Azúcar', emoji: '🎋' },
  { value: 'soya',    label: 'Soya',           emoji: '🫘' },
  { value: 'algodón', label: 'Algodón',        emoji: '🧶' },
  { value: 'otro',    label: 'Otro',           emoji: '📦' },
]

const UNITS = ['kg', 'ton', 'lb', 'quintal']

const fieldCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 transition-colors'
const labelCls = 'text-xs font-medium text-slate-700 block mb-1.5'

interface Props {
  open: boolean
  onClose: () => void
  preSelectedOrgId?: string
}

export function MintNFTModal({ open, onClose, preSelectedOrgId }: Props) {
  const mintAsset = useMintAsset()
  const toast     = useToast()
  const navigate  = useNavigate()

  // ─ Form state ──────────────────────────────────────────────────────────────
  const [productType,       setProductType]       = useState('')
  const [customProductType, setCustomProductType] = useState('')
  const [cargoName,         setCargoName]         = useState('')
  const [orgId,             setOrgId]             = useState(preSelectedOrgId ?? '')
  const [walletPubkey,      setWalletPubkey]      = useState('')
  const [weight,            setWeight]            = useState('')
  const [weightUnit,        setWeightUnit]        = useState('kg')
  const [qualityGrade,      setQualityGrade]      = useState('')
  const [origin,            setOrigin]            = useState('')
  const [description,       setDescription]       = useState('')
  const [errs,              setErrs]              = useState<Record<string, string>>({})
  const [isSubmitting,      setIsSubmitting]      = useState(false)

  // ─ Data ────────────────────────────────────────────────────────────────────
  const { data: orgsData }       = useOrganizations()
  const { data: orgWalletsData } = useOrgWallets(orgId)
  const { data: allWalletsData } = useWalletList({ status: 'active', limit: 200 })

  const orgs = orgsData?.items ?? []
  const availableWallets = orgId
    ? (orgWalletsData?.items ?? []).filter((w) => w.status === 'active')
    : (allWalletsData?.items ?? [])

  const handleOrgChange = (id: string) => {
    setOrgId(id)
    setWalletPubkey('')
  }

  const validate = () => {
    const e: Record<string, string> = {}
    const pt = productType === 'otro' ? customProductType.trim() : productType
    if (!pt)           e.productType  = 'Selecciona o escribe el tipo de producto'
    if (!walletPubkey) e.walletPubkey = 'Selecciona un wallet custodio inicial'
    if (weight && isNaN(Number(weight))) e.weight = 'Debe ser un número válido'
    setErrs(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setIsSubmitting(true)

    const finalProductType = productType === 'otro' ? customProductType.trim() : productType
    const metadata: Record<string, unknown> = {}
    if (cargoName)    metadata.name          = cargoName
    if (weight)       metadata.weight        = Number(weight)
    if (weight)       metadata.weight_unit   = weightUnit
    if (qualityGrade) metadata.quality_grade = qualityGrade
    if (origin)       metadata.origin        = origin
    if (description)  metadata.description   = description

    try {
      const res = await mintAsset.mutateAsync({
        product_type:             finalProductType,
        initial_custodian_wallet: walletPubkey,
        metadata,
      })
      toast.success('Carga registrada exitosamente')
      handleClose()
      navigate(`/assets/${res.asset.id}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al registrar la carga')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    setProductType(''); setCustomProductType(''); setCargoName('')
    setOrgId(preSelectedOrgId ?? ''); setWalletPubkey('')
    setWeight(''); setWeightUnit('kg'); setQualityGrade('')
    setOrigin(''); setDescription(''); setErrs({})
    onClose()
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Registrar nueva carga"
      description="Registra una nueva carga en la cadena de custodia con trazabilidad inmutable"
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose}>Cancelar</Button>
          <Button loading={isSubmitting} onClick={handleSubmit}>
            <Sparkles className="h-4 w-4" /> Registrar Carga
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-5">

        {/* 1 — Product type chips */}
        <div>
          <span className={labelCls}>Tipo de producto *</span>
          {errs.productType && <p className="text-xs text-red-600 mb-1">{errs.productType}</p>}
          <div className="flex flex-wrap gap-2">
            {PRODUCT_TYPES.map((pt) => (
              <button
                key={pt.value}
                type="button"
                onClick={() => { setProductType(pt.value); setErrs((e) => ({ ...e, productType: '' })) }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold border transition-all ${
                  productType === pt.value
                    ? 'bg-primary text-white border-primary shadow'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50 hover:bg-primary/10'
                }`}
              >
                <span>{pt.emoji}</span>
                <span>{pt.label}</span>
              </button>
            ))}
          </div>
          {productType === 'otro' && (
            <input
              type="text"
              placeholder="Especifica el tipo de producto..."
              value={customProductType}
              onChange={(e) => setCustomProductType(e.target.value)}
              className={`${fieldCls} mt-2`}
            />
          )}
        </div>

        {/* 2 — Cargo name */}
        <Input
          label="Nombre de la carga"
          placeholder="Ej: Tonelada de Café — Cosecha 2026"
          value={cargoName}
          onChange={(e) => setCargoName(e.target.value)}
          hint="Opcional pero recomendado para identificar rápidamente esta carga."
        />

        {/* 3 — Org → Wallet */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Organización / Finca</label>
            <select
              value={orgId}
              onChange={(e) => handleOrgChange(e.target.value)}
              className={fieldCls}
            >
              <option value="">— Sin filtro de org —</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Wallet custodio inicial *</label>
            {errs.walletPubkey && <p className="text-xs text-red-600 mb-1">{errs.walletPubkey}</p>}
            <select
              value={walletPubkey}
              onChange={(e) => { setWalletPubkey(e.target.value); setErrs((er) => ({ ...er, walletPubkey: '' })) }}
              className={`${fieldCls} ${errs.walletPubkey ? 'border-red-400' : ''}`}
            >
              <option value="">Selecciona wallet...</option>
              {availableWallets.map((w) => (
                <option key={w.id} value={w.wallet_pubkey}>
                  {w.name
                    ? `${w.name} (${w.wallet_pubkey.slice(0, 6)}…)`
                    : `${w.wallet_pubkey.slice(0, 8)}…${w.wallet_pubkey.slice(-4)}`}
                </option>
              ))}
            </select>
            {orgId && availableWallets.length === 0 && (
              <p className="text-xs text-amber-600 mt-1">Esta organización no tiene wallets activas.</p>
            )}
          </div>
        </div>

        {/* 4 — Weight */}
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Input
              label="Peso / Cantidad"
              placeholder="1000"
              type="number"
              min="0"
              value={weight}
              onChange={(e) => { setWeight(e.target.value); setErrs((er) => ({ ...er, weight: '' })) }}
              error={errs.weight}
            />
          </div>
          <div>
            <label className={labelCls}>Unidad</label>
            <select value={weightUnit} onChange={(e) => setWeightUnit(e.target.value)} className={fieldCls}>
              {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>

        {/* 5 — Optional metadata */}
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Calidad / Grado"
            placeholder="Premium, Grano grueso..."
            value={qualityGrade}
            onChange={(e) => setQualityGrade(e.target.value)}
          />
          <Input
            label="Origen"
            placeholder="Huila, Colombia"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
          />
        </div>

        <div>
          <label className={labelCls}>Descripción</label>
          <textarea
            placeholder="Características adicionales de la carga..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className={`${fieldCls} resize-none`}
          />
        </div>
      </div>
    </Dialog>
  )
}
