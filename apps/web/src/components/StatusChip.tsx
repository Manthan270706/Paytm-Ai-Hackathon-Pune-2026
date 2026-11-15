import { FC } from 'react'

export type CaseStatus =
  | 'NEW'
  | 'IN_PROGRESS'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'VERIFYING'
  | 'RESOLVED'
  | 'REJECTED'
  | 'CANCELLED'

const STATUS_CLASS: Record<CaseStatus, string> = {
  NEW: 'bg-status-new-bg text-status-new-text border-status-new-border',
  IN_PROGRESS: 'bg-status-progress-bg text-status-progress-text border-status-progress-border',
  AWAITING_APPROVAL: 'bg-status-approval-bg text-status-approval-text border-status-approval-border',
  APPROVED: 'bg-status-resolved-bg text-status-resolved-text border-status-resolved-border',
  VERIFYING: 'bg-status-new-bg text-status-verifying-text border-status-verifying-border',
  RESOLVED: 'bg-status-progress-bg text-status-progress-text border-status-resolved-border',
  REJECTED: 'bg-status-rejected-bg text-status-rejected-text border-status-rejected-border',
  CANCELLED: 'bg-surface-subtle text-ink-secondary border-surface-border',
}

const STATUS_LABEL: Record<CaseStatus, string> = {
  NEW: 'New',
  IN_PROGRESS: 'In progress',
  AWAITING_APPROVAL: 'Waiting for approval',
  APPROVED: 'Approved',
  VERIFYING: 'Verifying',
  RESOLVED: 'Resolved',
  REJECTED: 'Rejected',
  CANCELLED: 'Cancelled',
}

interface StatusChipProps {
  status: CaseStatus
  className?: string
  testId?: string
}

export const StatusChip: FC<StatusChipProps> = ({
  status,
  className = '',
  testId = 'status-chip',
}) => {
  const label = STATUS_LABEL[status]

  return (
    <span
      data-testid={testId}
      data-status={status}
      role="status"
      tabIndex={0}
      aria-label={label}
      className={`inline-flex items-center rounded-btn border px-2.5 py-0.5 font-sans text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${STATUS_CLASS[status]} ${className}`}
    >
      {label}
    </span>
  )
}
