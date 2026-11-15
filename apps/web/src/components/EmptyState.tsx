import { FC, ReactNode } from 'react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: FC<{ className?: string }>
  action?: ReactNode
  className?: string
  testId?: string
}

export const EmptyState: FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className = '',
  testId = 'empty-state',
}) => {
  return (
    <div
      data-testid={testId}
      className={`flex flex-col items-center justify-center p-8 text-center bg-surface-card rounded-xl border border-surface-border font-sans ${className}`}
    >
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-surface-subtle text-ink-secondary mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-ink-primary tracking-tight">
        {title}
      </h4>
      {description && (
        <p className="text-xs text-ink-secondary mt-1 max-w-sm">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
