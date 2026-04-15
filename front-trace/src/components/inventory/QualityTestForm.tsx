import { useState } from 'react'
import { Beaker, Loader2 } from 'lucide-react'

import { useCreateQualityTest } from '@/hooks/useQualityTests'
import { useToast } from '@/store/toast'
import {
  QUALITY_TEST_LABEL,
  QUALITY_TEST_TYPES,
  QUALITY_TEST_UNIT,
  type QualityTestType,
} from '@/types/commodity'

interface Props {
  batchId: string
  onCreated?: () => void
}

export function QualityTestForm({ batchId, onCreated }: Props) {
  const create = useCreateQualityTest()
  const toast = useToast()

  const [testType, setTestType] = useState<QualityTestType>('humidity')
  const [value, setValue] = useState('')
  const [unit, setUnit] = useState(QUALITY_TEST_UNIT.humidity)
  const [thresholdMin, setThresholdMin] = useState('')
  const [thresholdMax, setThresholdMax] = useState('')
  const [lab, setLab] = useState('')
  const [testDate, setTestDate] = useState(new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')

  function onTypeChange(t: QualityTestType) {
    setTestType(t)
    // Auto-fill unit from the type if the user hasn't customized it.
    const defaultUnit = QUALITY_TEST_UNIT[t]
    if (defaultUnit) setUnit(defaultUnit)
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!value) {
      toast.error('Ingresa un valor')
      return
    }
    try {
      await create.mutateAsync({
        batch_id: batchId,
        test_type: testType,
        value: Number(value),
        unit: unit || 'unit',
        threshold_min: thresholdMin ? Number(thresholdMin) : null,
        threshold_max: thresholdMax ? Number(thresholdMax) : null,
        lab: lab || null,
        test_date: testDate,
        notes: notes || null,
      })
      toast.success('Test registrado')
      setValue('')
      setNotes('')
      onCreated?.()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al registrar'
      toast.error(msg)
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-border/60 bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <Beaker className="h-4 w-4 text-primary" />
        Nuevo test de calidad
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-medium uppercase text-muted-foreground">Tipo</label>
          <select
            value={testType}
            onChange={(e) => onTypeChange(e.target.value as QualityTestType)}
            className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {QUALITY_TEST_TYPES.map((t) => (
              <option key={t} value={t}>
                {QUALITY_TEST_LABEL[t]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase text-muted-foreground">Unidad</label>
          <input
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase text-muted-foreground">Valor *</label>
          <input
            type="number"
            step="any"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
            className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase text-muted-foreground">Fecha *</label>
          <input
            type="date"
            value={testDate}
            onChange={(e) => setTestDate(e.target.value)}
            required
            className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase text-muted-foreground">Umbral mínimo</label>
          <input
            type="number"
            step="any"
            value={thresholdMin}
            onChange={(e) => setThresholdMin(e.target.value)}
            className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium uppercase text-muted-foreground">Umbral máximo</label>
          <input
            type="number"
            step="any"
            value={thresholdMax}
            onChange={(e) => setThresholdMax(e.target.value)}
            className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      <div>
        <label className="text-[10px] font-medium uppercase text-muted-foreground">Laboratorio</label>
        <input
          value={lab}
          onChange={(e) => setLab(e.target.value)}
          className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      <div>
        <label className="text-[10px] font-medium uppercase text-muted-foreground">Notas</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full resize-none rounded-lg border border-border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <button
        type="submit"
        disabled={create.isPending}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:opacity-60"
      >
        {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Registrar test
      </button>
    </form>
  )
}
