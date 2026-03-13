import { useState, useMemo, type ReactNode } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface Column<T> {
  key: string
  header: string
  sortable?: boolean
  hideOnMobile?: boolean
  /** Custom cell renderer — receives the full row */
  render?: (row: T) => ReactNode
  /** Simple accessor when render is not provided */
  accessor?: (row: T) => ReactNode
  className?: string
  headerClassName?: string
}

export interface PaginationConfig {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

export interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  /** Unique key extractor per row (defaults to index) */
  rowKey?: (row: T, index: number) => string | number
  onRowClick?: (row: T) => void
  pagination?: PaginationConfig
  emptyMessage?: string
  isLoading?: boolean
  /** Extra className on container */
  className?: string
  /** Disable the mobile card layout (force table always) */
  forceTable?: boolean
}

type SortDir = 'asc' | 'desc'

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DataTable<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  pagination,
  emptyMessage = 'Sin resultados',
  isLoading,
  className,
  forceTable,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    if (!sortKey) return data
    const col = columns.find((c) => c.key === sortKey)
    if (!col) return data
    return [...data].sort((a, b) => {
      const va = col.accessor ? col.accessor(a) : (a as any)[col.key]
      const vb = col.accessor ? col.accessor(b) : (b as any)[col.key]
      const sa = va == null ? '' : String(va)
      const sb = vb == null ? '' : String(vb)
      const cmp = sa.localeCompare(sb, undefined, { numeric: true, sensitivity: 'base' })
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir, columns])

  const getKey = (row: T, i: number) => (rowKey ? rowKey(row, i) : i)

  const getCellContent = (col: Column<T>, row: T) => {
    if (col.render) return col.render(row)
    if (col.accessor) return col.accessor(row)
    return (row as any)[col.key] ?? '—'
  }

  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1

  /* ---- Loading / Empty ---- */
  if (isLoading) {
    return (
      <div className={cn('rounded-2xl border border-slate-200/60 bg-white shadow-sm', className)}>
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className={cn('rounded-2xl border border-slate-200/60 bg-white shadow-sm', className)}>
        <div className="py-16 text-center text-sm text-slate-400">{emptyMessage}</div>
      </div>
    )
  }

  /* ---- Mobile Cards ---- */
  const mobileCards = !forceTable && (
    <div className="space-y-3 md:hidden">
      {sorted.map((row, i) => (
        <div
          key={getKey(row, i)}
          onClick={onRowClick ? () => onRowClick(row) : undefined}
          className={cn(
            'rounded-xl border border-slate-200/60 bg-white p-4 shadow-sm space-y-2',
            onRowClick && 'cursor-pointer hover:border-indigo-200 hover:shadow-md transition-all active:scale-[0.99]',
          )}
        >
          {columns.map((col) => (
            <div key={col.key} className="flex items-start justify-between gap-3">
              <span className="text-xs font-medium text-slate-400 shrink-0">{col.header}</span>
              <span className="text-sm text-slate-700 text-right min-w-0">{getCellContent(col, row)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )

  /* ---- Desktop Table ---- */
  const desktopTable = (
    <div className={cn('overflow-x-auto rounded-2xl border border-slate-200/60 bg-white shadow-sm', !forceTable && 'hidden md:block')}>
      <table className="w-full text-sm min-w-[600px]">
        <thead>
          <tr className="border-b border-slate-100">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500',
                  col.sortable && 'cursor-pointer select-none hover:text-slate-700',
                  col.headerClassName,
                )}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {col.sortable && (
                    <span className="text-slate-300">
                      {sortKey === col.key ? (
                        sortDir === 'asc' ? (
                          <ChevronUp className="h-3.5 w-3.5 text-indigo-500" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5 text-indigo-500" />
                        )
                      ) : (
                        <ChevronsUpDown className="h-3.5 w-3.5" />
                      )}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {sorted.map((row, i) => (
            <tr
              key={getKey(row, i)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                'transition-colors',
                onRowClick && 'cursor-pointer hover:bg-slate-50/80',
              )}
            >
              {columns.map((col) => (
                <td key={col.key} className={cn('px-4 py-3 text-slate-700', col.className)}>
                  {getCellContent(col, row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  /* ---- Pagination ---- */
  const paginationBar = pagination && totalPages > 1 && (
    <div className="flex items-center justify-between px-1 pt-4">
      <span className="text-xs text-slate-400">
        {pagination.total} resultado{pagination.total !== 1 ? 's' : ''}
      </span>
      <div className="flex items-center gap-2">
        <button
          disabled={pagination.page <= 0}
          onClick={() => pagination.onPageChange(pagination.page - 1)}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-xs font-medium text-slate-600 tabular-nums min-w-[4rem] text-center">
          {pagination.page + 1} / {totalPages}
        </span>
        <button
          disabled={pagination.page >= totalPages - 1}
          onClick={() => pagination.onPageChange(pagination.page + 1)}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )

  return (
    <div className={className}>
      {mobileCards}
      {desktopTable}
      {paginationBar}
    </div>
  )
}
