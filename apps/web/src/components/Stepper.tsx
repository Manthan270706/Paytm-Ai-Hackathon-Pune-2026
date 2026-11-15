import { FC } from 'react'
import { Check, Clock } from 'lucide-react'

export type StepState = 'completed' | 'current' | 'upcoming'

export interface StepItem {
  id: string
  label: string
  description?: string
  state: StepState
  timestamp?: string
}

interface StepperProps {
  steps: StepItem[]
  nextUpdateText?: string
  className?: string
  testId?: string
}

export const Stepper: FC<StepperProps> = ({
  steps,
  nextUpdateText,
  className = '',
  testId = 'stepper',
}) => {
  return (
    <div
      data-testid={testId}
      className={`w-full bg-surface-card rounded-xl border border-surface-border p-4 font-sans ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-paytm-navy">Case Resolution Progress</h4>
        {nextUpdateText && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-status-progress-text bg-status-progress-bg border border-status-progress-border px-2 py-0.5 rounded-full">
            <Clock className="w-3 h-3 text-status-progress-text" />
            {nextUpdateText}
          </span>
        )}
      </div>

      <ol className="relative flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-2">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1
          const isCompleted = step.state === 'completed'
          const isCurrent = step.state === 'current'

          return (
            <li
              key={step.id}
              className={`flex sm:flex-col items-center gap-3 sm:gap-1.5 flex-1 w-full sm:text-center ${
                isCurrent ? 'opacity-100' : isCompleted ? 'opacity-90' : 'opacity-60'
              }`}
            >
              {/* Connector line for mobile and desktop */}
              <div className="flex sm:flex-col items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold transition ${
                    isCompleted
                      ? 'bg-paytm-navy text-white shadow-sm'
                      : isCurrent
                      ? 'bg-paytm-cyan text-paytm-navy ring-4 ring-paytm-cyan-light font-black'
                      : 'bg-surface-subtle text-ink-muted border border-surface-border'
                  }`}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isCompleted ? <Check className="w-4 h-4" /> : index + 1}
                </div>

                {!isLast && (
                  <div
                    className={`hidden sm:block h-0.5 w-full mt-2 transition ${
                      isCompleted ? 'bg-paytm-navy' : 'bg-surface-divider'
                    }`}
                  />
                )}
              </div>

              {/* Label & Details */}
              <div className="flex-1 sm:mt-1">
                <p
                  className={`text-xs font-semibold ${
                    isCurrent
                      ? 'text-paytm-navy'
                      : isCompleted
                      ? 'text-ink-primary'
                      : 'text-ink-muted'
                  }`}
                >
                  {step.label}
                </p>
                {step.description && (
                  <p className="text-[11px] text-ink-secondary mt-0.5 hidden sm:block">
                    {step.description}
                  </p>
                )}
                {step.timestamp && (
                  <p className="text-[10px] text-ink-muted font-mono mt-0.5">
                    {step.timestamp}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
