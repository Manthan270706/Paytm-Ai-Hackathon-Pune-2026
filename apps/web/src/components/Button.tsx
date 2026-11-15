import { FC, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps {
  children: ReactNode
  onClick?: () => void
  type?: 'button' | 'submit' | 'reset'
  variant?: ButtonVariant
  disabled?: boolean
  className?: string
  testId?: string
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: 'bg-paytm-navy text-surface-card hover:bg-paytm-navy-hover',
  secondary: 'border border-paytm-navy bg-surface-card text-paytm-navy hover:bg-paytm-cyan-light',
  ghost: 'bg-transparent text-paytm-navy hover:bg-paytm-cyan-light',
}

export const Button: FC<ButtonProps> = ({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  disabled = false,
  className = '',
  testId = 'button',
}) => {
  return (
    <button
      type={type}
      data-testid={testId}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex min-h-12 items-center justify-center rounded-btn px-4 font-sans text-base font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan focus-visible:ring-offset-2 disabled:bg-surface-subtle disabled:text-ink-disabled ${VARIANT_CLASS[variant]} ${className}`}
    >
      {children}
    </button>
  )
}
