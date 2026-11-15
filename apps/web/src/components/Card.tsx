import { FC, KeyboardEvent, ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  onActivate?: () => void
  className?: string
  testId?: string
}

export const Card: FC<CardProps> = ({
  title,
  children,
  onActivate,
  className = '',
  testId = 'card',
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
      className={`rounded-card border border-surface-border bg-surface-card p-4 font-sans shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${className}`}
    >
      {title ? <h2 className="text-base font-medium text-ink-primary">{title}</h2> : null}
      <div className={title ? 'mt-2 text-sm text-ink-secondary' : 'text-sm text-ink-secondary'}>
        {children}
      </div>
    </div>
  )
}
