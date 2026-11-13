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
  let badgeStyle = 'bg-slate-800 text-slate-300 border-slate-700'
  let label = source

  if (source === 'PAYTM_STAGING') {
    badgeStyle = 'bg-sky-950/80 text-sky-400 border-sky-800/80 shadow-sky-950/20'
    label = 'PAYTM STAGING'
  } else if (source === 'SYNTHETIC_DEMO') {
    badgeStyle = 'bg-amber-950/80 text-amber-400 border-amber-800/80 shadow-amber-950/20'
    label = 'SYNTHETIC DEMO'
  } else if (source === 'INTEGRATION_UNAVAILABLE' || source === 'UNAVAILABLE') {
    badgeStyle = 'bg-rose-950/80 text-rose-400 border-rose-800/80 shadow-rose-950/20'
    label = 'INTEGRATION UNAVAILABLE'
  } else if (source === 'MOCK' || source === 'MOCK_SETTLEMENT_OPS') {
    badgeStyle = 'bg-purple-950/80 text-purple-400 border-purple-800/80 shadow-purple-950/20'
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
