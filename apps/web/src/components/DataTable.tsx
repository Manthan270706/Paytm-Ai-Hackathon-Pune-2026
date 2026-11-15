import { ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: string
  width?: string
  className?: string
  render: (item: T) => ReactNode
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (item: T) => string
  onRowClick?: (item: T) => void
  selectedKey?: string | null
  emptyMessage?: string
  className?: string
  testId?: string
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  selectedKey,
  emptyMessage = 'No records found.',
  className = '',
  testId = 'data-table',
}: DataTableProps<T>) {
  return (
    <div
      data-testid={testId}
      className={`w-full overflow-hidden rounded-xl border border-surface-border bg-surface-card shadow-sm font-sans ${className}`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-surface-border bg-surface-canvas text-xs font-semibold text-ink-secondary">
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={{ width: col.width }}
                  className={`px-4 py-3.5 ${col.className || ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-divider">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-sm text-ink-muted"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item) => {
                const key = keyExtractor(item)
                const isSelected = selectedKey === key
                const isClickable = Boolean(onRowClick)

                return (
                  <tr
                    key={key}
                    tabIndex={isClickable ? 0 : undefined}
                    role={isClickable ? 'button' : undefined}
                    onClick={() => onRowClick?.(item)}
                    onKeyDown={(e) => {
                      if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault()
                        onRowClick?.(item)
                      }
                    }}
                    className={`transition ${
                      isSelected
                        ? 'bg-paytm-cyan-light/60 font-medium'
                        : isClickable
                        ? 'hover:bg-surface-subtle cursor-pointer'
                        : ''
                    }`}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`px-4 py-3.5 text-ink-primary ${col.className || ''}`}
                      >
                        {col.render(item)}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {data.length > 0 && (
        <div className="px-4 py-2.5 bg-surface-canvas border-t border-surface-divider flex items-center justify-between text-xs text-ink-secondary">
          <span>Showing {data.length} records</span>
          <span className="font-mono text-[11px] text-ink-muted">Settlement Reconciliation Ledger</span>
        </div>
      )}
    </div>
  )
}
