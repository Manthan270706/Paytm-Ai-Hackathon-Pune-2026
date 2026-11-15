import { FC, KeyboardEvent } from 'react'

interface InputProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  onEnter?: () => void
  type?: 'text' | 'search' | 'email'
  placeholder?: string
  disabled?: boolean
  className?: string
  testId?: string
}

export const Input: FC<InputProps> = ({
  id,
  label,
  value,
  onChange,
  onEnter,
  type = 'text',
  placeholder,
  disabled = false,
  className = '',
  testId = 'input',
}) => {
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      onEnter?.()
    }
  }

  return (
    <div className={`flex flex-col gap-2 font-sans ${className}`}>
      <label htmlFor={id} className="text-sm font-medium text-ink-secondary">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        data-testid={testId}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        className="min-h-12 rounded-btn border border-surface-border bg-surface-subtle px-4 font-sans text-base text-ink-primary placeholder:text-ink-disabled focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan disabled:text-ink-disabled"
      />
    </div>
  )
}
