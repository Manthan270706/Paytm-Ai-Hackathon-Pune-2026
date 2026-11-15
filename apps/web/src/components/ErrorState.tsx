import { FC, ReactNode, useState } from 'react'
import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  details?: string
  onRetry?: () => void
  retryLabel?: string
  isRetrying?: boolean
  className?: string
  testId?: string
  action?: ReactNode
}

export const ErrorState: FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  details,
  onRetry,
  retryLabel = 'Try again',
  isRetrying = false,
  className = '',
  testId = 'error-state',
  action,
}) => {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div
      role="alert"
      data-testid={testId}
      className={`flex flex-col items-center justify-center p-6 text-center bg-status-rejected-bg rounded-xl border border-status-rejected-border font-sans ${className}`}
    >
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-status-rejected-border/40 text-status-rejected-text mb-3">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-status-rejected-text tracking-tight">
        {title}
      </h4>
      <p className="text-xs text-ink-secondary mt-1 max-w-sm">
        {message}
      </p>

      {details && (
        <div className="w-full max-w-md mt-3">
          <button
            type="button"
            onClick={() => setShowDetails((prev) => !prev)}
            className="flex items-center justify-center gap-1 text-[11px] font-medium text-ink-secondary hover:text-ink-primary transition mx-auto"
          >
            <span>{showDetails ? 'Hide technical details' : 'Show technical details'}</span>
            {showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {showDetails && (
            <pre className="mt-2 p-2.5 text-left text-[11px] font-mono text-status-rejected-text bg-surface-card rounded-lg border border-status-rejected-border overflow-x-auto max-h-32">
              {details}
            </pre>
          )}
        </div>
      )}

      {(onRetry || action) && (
        <div className="mt-4 flex items-center gap-2">
          {onRetry && (
            <button
              type="button"
              data-testid={`${testId}-retry`}
              onClick={onRetry}
              disabled={isRetrying}
              className="inline-flex min-h-12 items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-status-rejected-text text-white hover:opacity-90 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
              <span>{retryLabel}</span>
            </button>
          )}
          {action}
        </div>
      )}
    </div>
  )
}
