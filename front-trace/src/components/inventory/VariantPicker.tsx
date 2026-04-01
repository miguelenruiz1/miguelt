import { useProductVariantsForProduct } from '@/hooks/useInventory'

interface VariantPickerProps {
  productId: string | undefined
  value: string
  onChange: (variantId: string, salePrice?: number) => void
  className?: string
}

export function VariantPicker({ productId, value, onChange, className }: VariantPickerProps) {
  const { data: variants } = useProductVariantsForProduct(productId)

  if (!variants || variants.length === 0) return null

  function handleChange(variantId: string) {
    if (!variantId) {
      onChange('', undefined)
      return
    }
    const v = variants!.find(x => x.id === variantId)
    onChange(variantId, v && v.sale_price > 0 ? v.sale_price : undefined)
  }

  return (
    <select
      value={value}
      onChange={e => handleChange(e.target.value)}
      className={className ?? 'rounded-xl border border-border px-2 py-1.5 text-xs focus:ring-2 focus:ring-ring outline-none'}
    >
      <option value="">— Sin variante —</option>
      {variants.map(v => {
        const opts = v.option_values ? Object.values(v.option_values).join(', ') : ''
        return (
          <option key={v.id} value={v.id}>
            {v.sku} — {v.name}{opts ? ` (${opts})` : ''}
          </option>
        )
      })}
    </select>
  )
}
