import { useState } from 'react'
import { FileCheck, Download, Copy, RefreshCw, Search } from 'lucide-react'
import { useCertificates, useRegenerateCertificate } from '@/hooks/useCompliance'
import { complianceApi } from '@/lib/compliance-api'
import { useToast } from '@/store/toast'
import { DataTable, type Column } from '@/components/ui/datatable'
import { SkeletonTable } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { ComplianceCertificate, CertificateStatus } from '@/types/compliance'

// ─── Status badge mapping ────────────────────────────────────────────────────

const statusVariant: Record<string, 'success' | 'warning' | 'muted' | 'danger' | 'default'> = {
  generating: 'warning',
  active: 'success',
  superseded: 'muted',
  revoked: 'danger',
  expired: 'muted',
}

const statusLabel: Record<string, string> = {
  generating: 'Generando',
  active: 'Activo',
  superseded: 'Reemplazado',
  revoked: 'Revocado',
  expired: 'Expirado',
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function CertificatesPage() {
  const toast = useToast()
  const regenerate = useRegenerateCertificate()

  // Filters
  const [filterSlug, setFilterSlug] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterYear, setFilterYear] = useState('')

  const params = {
    framework_slug: filterSlug || undefined,
    status: filterStatus || undefined,
    year: filterYear ? Number(filterYear) : undefined,
  }

  const { data, isLoading } = useCertificates(params)
  const certificates = data?.items ?? []
  const total = data?.total ?? 0

  // Pagination
  const [page, setPage] = useState(0)
  const pageSize = 25

  async function handleRegenerate(id: string) {
    try {
      await regenerate.mutateAsync(id)
      toast.success('Certificado regenerado')
    } catch (e: any) {
      toast.error(e.message ?? 'Error al regenerar')
    }
  }

  function handleCopyVerifyUrl(cert: ComplianceCertificate) {
    const url = cert.verify_url.startsWith('http')
      ? cert.verify_url
      : `${window.location.origin}${cert.verify_url}`
    navigator.clipboard.writeText(url)
    toast.success('URL de verificacion copiada')
  }

  async function handleDownload(cert: ComplianceCertificate) {
    if (!cert.pdf_url) {
      toast.warning('PDF no disponible aún')
      return
    }
    try {
      await complianceApi.certificates.download(cert.id, `${cert.certificate_number}.pdf`)
    } catch (e: any) {
      toast.error(e?.message ?? 'No se pudo descargar el PDF')
    }
  }

  const columns: Column<ComplianceCertificate>[] = [
    {
      key: 'certificate_number',
      header: 'Numero',
      sortable: true,
      render: (row) => (
        <span className="font-mono text-xs font-medium text-foreground">{row.certificate_number}</span>
      ),
    },
    {
      key: 'asset_id',
      header: 'Asset',
      render: (row) => (
        <span className="text-xs text-muted-foreground font-mono truncate max-w-[120px] inline-block" title={row.asset_id}>
          {row.asset_id.slice(0, 8)}...
        </span>
      ),
    },
    {
      key: 'framework_slug',
      header: 'Framework',
      sortable: true,
      render: (row) => (
        <Badge variant="info">{row.framework_slug.toUpperCase()}</Badge>
      ),
    },
    {
      key: 'metadata_commodity',
      header: 'Commodity',
      render: (row) => {
        const commodity = (row.metadata as any)?.commodity_type
        return commodity
          ? <span className="text-sm text-muted-foreground capitalize">{commodity}</span>
          : <span className="text-xs text-muted-foreground">--</span>
      },
    },
    {
      key: 'metadata_quantity',
      header: 'Cantidad',
      render: (row) => {
        const qty = (row.metadata as any)?.quantity_kg
        return qty != null
          ? <span className="text-sm text-muted-foreground tabular-nums">{Number(qty).toLocaleString('es-CO')} kg</span>
          : <span className="text-xs text-muted-foreground">--</span>
      },
    },
    {
      key: 'status',
      header: 'Estado',
      sortable: true,
      render: (row) => (
        <Badge variant={statusVariant[row.status] ?? 'default'} dot>
          {statusLabel[row.status] ?? row.status}
        </Badge>
      ),
    },
    {
      key: 'valid_until',
      header: 'Valido hasta',
      sortable: true,
      render: (row) => (
        <span className="text-sm text-muted-foreground tabular-nums">
          {new Date(row.valid_until).toLocaleDateString('es-CO', {
            year: 'numeric', month: 'short', day: 'numeric',
          })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div className="flex items-center gap-1 justify-end">
          <button
            onClick={() => handleDownload(row)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-muted-foreground hover:bg-secondary transition-colors"
            title="Descargar PDF"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => handleCopyVerifyUrl(row)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-muted-foreground hover:bg-secondary transition-colors"
            title="Copiar URL de verificacion"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => handleRegenerate(row.id)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
            title="Regenerar"
            disabled={regenerate.isPending}
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ]

  const currentYear = new Date().getFullYear()
  const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50">
            <FileCheck className="h-5 w-5 text-violet-600" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Certificados</h1>
            <p className="text-sm text-muted-foreground">Certificados de cumplimiento emitidos</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={filterSlug}
            onChange={(e) => { setFilterSlug(e.target.value); setPage(0) }}
            placeholder="Framework slug..."
            className="h-9 rounded-lg border border-gray-300 pl-9 pr-3 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none w-48"
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(0) }}
          className="h-9 rounded-lg border border-gray-300 px-3 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none"
        >
          <option value="">Todos los estados</option>
          <option value="active">Activo</option>
          <option value="generating">Generando</option>
          <option value="superseded">Reemplazado</option>
          <option value="revoked">Revocado</option>
          <option value="expired">Expirado</option>
        </select>
        <select
          value={filterYear}
          onChange={(e) => { setFilterYear(e.target.value); setPage(0) }}
          className="h-9 rounded-lg border border-gray-300 px-3 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none"
        >
          <option value="">Todos los anos</option>
          {yearOptions.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        {(filterSlug || filterStatus || filterYear) && (
          <button
            onClick={() => { setFilterSlug(''); setFilterStatus(''); setFilterYear(''); setPage(0) }}
            className="text-xs text-primary hover:text-primary font-medium"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={certificates}
        rowKey={(row) => row.id}
        isLoading={isLoading}
        loadingState={<SkeletonTable columns={6} rows={8} />}
        emptyState={
          <EmptyState
            icon={FileCheck}
            title="Sin certificados emitidos"
            description="Genera un certificado desde un registro de cumplimiento para verlo acá."
          />
        }
        emptyMessage="No hay certificados emitidos. Genera uno desde un registro de cumplimiento."
        pagination={total > pageSize ? {
          page,
          pageSize,
          total,
          onPageChange: setPage,
        } : undefined}
      />
    </div>
  )
}
