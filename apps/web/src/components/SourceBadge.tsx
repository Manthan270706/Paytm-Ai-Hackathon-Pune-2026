import { FC } from 'react'
import { SourceType } from '../types/api'

interface SourceBadgeProps {
  source?: SourceType | string
  className?: string
  size?: 'sm' | 'md'
}

export const SourceBadge: FC<SourceBadgeProps> = ({
  source = 'SYNTHETIC_DEMO',
  className = '',
  size = 'sm',
}) => {
  let badgeStyle = 'bg-surface-subtle text-ink-secondary border-surface-border'
  let label = source

  if (source === 'PAYTM_STAGING') {
    badgeStyle = 'bg-paytm-cyan-light text-paytm-navy border-paytm-cyan/30'
    label = 'PAYTM STAGING'
  } else if (source === 'SYNTHETIC_DEMO') {
    badgeStyle = 'bg-status-approval-bg text-status-approval-text border-status-approval-border'
    label = 'SYNTHETIC DEMO'
  } else if (source === 'INTEGRATION_UNAVAILABLE' || source === 'UNAVAILABLE') {
    badgeStyle = 'bg-status-rejected-bg text-status-rejected-text border-status-rejected-border'
    label = 'INTEGRATION UNAVAILABLE'
  } else if (source === 'MOCK' || source === 'MOCK_SETTLEMENT_OPS') {
    badgeStyle = 'bg-surface-subtle text-ink-secondary border-surface-border'
    label = 'MOCK ADAPTER'
  }

  const sizeStyle = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1'

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-medium tracking-wider uppercase rounded-md border shadow-sm ${badgeStyle} ${sizeStyle} ${className}`}
      title={`Data Provenance: ${source}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70 animate-pulse" />
      {label}
    </span>
  )
}
