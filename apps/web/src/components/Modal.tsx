import { FC, ReactNode, useEffect, useCallback } from 'react'
import { X } from 'lucide-react'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl'
  testId?: string
}

const MAX_WIDTH_CLASS = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
}

export const Modal: FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  maxWidth = 'md',
  testId = 'modal',
}) => {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    },
    [onClose]
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${testId}-title`}
      data-testid={testId}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={`w-full ${MAX_WIDTH_CLASS[maxWidth]} rounded-2xl bg-surface-card border border-surface-border shadow-modal overflow-hidden flex flex-col max-h-[90vh]`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-divider">
          <div>
            <h3 id={`${testId}-title`} className="text-lg font-semibold text-ink-primary font-sans">
              {title}
            </h3>
            {subtitle && (
              <p className="text-xs text-ink-secondary mt-0.5 font-sans">
                {subtitle}
              </p>
            )}
          </div>
          <button
            type="button"
            data-testid={`${testId}-close`}
            onClick={onClose}
            aria-label="Close dialog"
            className="flex items-center justify-center w-10 h-10 min-h-12 min-w-12 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-surface-subtle transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 overflow-y-auto font-sans text-sm text-ink-primary">
          {children}
        </div>

        {/* Optional Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-divider bg-surface-canvas">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
