import { FC, useEffect } from 'react'
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react'

export type ToastVariant = 'success' | 'warning' | 'error' | 'info'

interface ToastProps {
  id?: string
  variant?: ToastVariant
  title: string
  message?: string
  isOpen: boolean
  onClose: () => void
  durationMs?: number
  testId?: string
}

const VARIANT_CONFIG = {
  success: {
    icon: CheckCircle2,
    containerClass: 'bg-status-completed-bg border-status-completed-border text-status-completed-text',
    iconClass: 'text-status-completed-text',
  },
  warning: {
    icon: AlertTriangle,
    containerClass: 'bg-status-approval-bg border-status-approval-border text-status-approval-text',
    iconClass: 'text-status-approval-text',
  },
  error: {
    icon: XCircle,
    containerClass: 'bg-status-rejected-bg border-status-rejected-border text-status-rejected-text',
    iconClass: 'text-status-rejected-text',
  },
  info: {
    icon: Info,
    containerClass: 'bg-status-progress-bg border-status-progress-border text-status-progress-text',
    iconClass: 'text-status-progress-text',
  },
}

export const Toast: FC<ToastProps> = ({
  variant = 'info',
  title,
  message,
  isOpen,
  onClose,
  durationMs = 4000,
  testId = 'toast',
}) => {
  useEffect(() => {
    if (isOpen && durationMs > 0) {
      const timer = setTimeout(() => {
        onClose()
      }, durationMs)
      return () => clearTimeout(timer)
    }
  }, [isOpen, durationMs, onClose])

  if (!isOpen) return null

  const config = VARIANT_CONFIG[variant]
  const IconComponent = config.icon

  return (
    <aside
      role="alert"
      aria-live="polite"
      data-testid={testId}
      className={`fixed bottom-4 right-4 z-50 flex items-start gap-3 p-4 rounded-xl border shadow-card max-w-sm w-full font-sans transition-all ${config.containerClass}`}
    >
      <IconComponent className={`w-5 h-5 shrink-0 mt-0.5 ${config.iconClass}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold tracking-tight">{title}</p>
        {message && <p className="text-xs mt-0.5 opacity-90">{message}</p>}
      </div>
      <button
        type="button"
        data-testid={`${testId}-close`}
        onClick={onClose}
        aria-label="Close notification"
        className="shrink-0 p-1 min-w-10 min-h-10 flex items-center justify-center rounded-lg hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
      >
        <X className="w-4 h-4" />
      </button>
    </aside>
  )
}
