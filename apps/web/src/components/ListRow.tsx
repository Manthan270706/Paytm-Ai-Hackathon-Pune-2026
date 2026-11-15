import { FC, KeyboardEvent, ReactNode } from 'react'

interface ListRowProps {
  title: string
  subtitle?: string
  amount: string
  onActivate?: () => void
  trailing?: ReactNode
  className?: string
  testId?: string
}

export const ListRow: FC<ListRowProps> = ({
  title,
  subtitle,
  amount,
  onActivate,
  trailing,
  className = '',
  testId = 'list-row',
}) => {
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!onActivate) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onActivate()
    }
  }

  return (
    <div
      data-testid={testId}
      role={onActivate ? 'button' : undefined}
      tabIndex={onActivate ? 0 : undefined}
      onClick={onActivate}
      onKeyDown={onActivate ? handleKeyDown : undefined}
      className={`flex min-h-12 w-full items-center gap-2 border-b border-surface-divider p-2.5 font-sans focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${className}`}
    >
      <div className="min-w-0 flex-1">
        <p className="text-base font-medium text-ink-primary">{title}</p>
        {subtitle ? <p className="text-xs font-medium text-ink-muted">{subtitle}</p> : null}
      </div>
      <p
        data-testid={`${testId}-amount`}
        className="shrink-0 text-right text-base font-semibold text-ink-primary tabular-nums"
      >
        {amount}
      </p>
      {trailing}
    </div>
  )
}
