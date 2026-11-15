import { useState, FC } from 'react'
import { SupportCaseItem, ApprovalSummary } from '../types/api'
import { XCircle, X, AlertCircle } from 'lucide-react'
import { Button } from './Button'

interface RejectModalProps {
  isOpen: boolean
  onClose: () => void
  caseItem: SupportCaseItem | null
  pendingApproval: ApprovalSummary | null
  onConfirmReject: (
    caseId: string,
    version: number,
    actionHash: string,
    reason: string
  ) => Promise<void>
  isRejecting: boolean
}

const PRESET_REASONS = [
  'Requires manual bank statement verification',
  'Incorrect order reference cited by merchant',
  'Duplicate investigation already in progress',
  'Discrepancy pending bank UTR confirmation',
]

export const RejectModal: FC<RejectModalProps> = ({
  isOpen,
  onClose,
  caseItem,
  pendingApproval,
  onConfirmReject,
  isRejecting,
}) => {
  const [reason, setReason] = useState('')
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)

  if (!isOpen || !caseItem) return null

  const actionHash =
    pendingApproval?.action_hash ||
    '44efa879046efa3a441c61673e778f5ed3cb2adec16c9d57ca0f88b6139a2e02'

  const isReasonValid = reason.trim().length > 0

  const handleReject = async () => {
    setHasAttemptedSubmit(true)
    if (!isReasonValid) return

    await onConfirmReject(caseItem.id, caseItem.version, actionHash, reason.trim())
    setReason('')
    setHasAttemptedSubmit(false)
    onClose()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reject-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/50 backdrop-blur-sm animate-in fade-in duration-200 font-sans"
    >
      <div className="bg-surface-card border border-surface-border rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-5 text-ink-primary">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-surface-divider pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-status-rejected-bg border border-status-rejected-border text-status-rejected-text">
              <XCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 id="reject-modal-title" className="text-base font-bold text-paytm-navy tracking-tight">
                Reject Gated Action
              </h3>
              <p className="text-xs text-ink-secondary">
                Settlement Re-Sync Rejection (Case {caseItem.case_number})
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isRejecting}
            aria-label="Close dialog"
            className="flex items-center justify-center w-10 h-10 min-h-12 min-w-12 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-surface-subtle transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Warning info */}
        <div className="p-3 bg-status-rejected-bg border border-status-rejected-border rounded-xl text-xs text-status-rejected-text flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            Rejecting this action cancels the pending automated settlement re-sync. An immutable audit event with your documented justification will be written to the case timeline.
          </div>
        </div>

        {/* Rejection Reason Form */}
        <div className="space-y-2 text-xs">
          <label className="block font-semibold text-ink-primary">
            Rejection Reason <span className="text-status-rejected-text">*</span>
            <span className="text-ink-muted font-normal ml-1">
              (Mandatory for audit trail governance)
            </span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => {
              setReason(e.target.value)
              if (hasAttemptedSubmit) setHasAttemptedSubmit(false)
            }}
            placeholder="Document the exact justification for rejecting this settlement re-sync..."
            rows={3}
            className={`w-full p-3 bg-surface-subtle rounded-xl border text-xs text-ink-primary placeholder:text-ink-muted outline-none transition ${
              hasAttemptedSubmit && !isReasonValid
                ? 'border-status-rejected-border focus:border-status-rejected-text'
                : 'border-surface-border focus:border-paytm-cyan'
            }`}
          />
          {hasAttemptedSubmit && !isReasonValid && (
            <p className="text-[11px] text-status-rejected-text font-medium">
              Please enter a rejection reason before confirming.
            </p>
          )}

          {/* Quick presets */}
          <div className="pt-1">
            <span className="text-[10px] text-ink-muted uppercase tracking-wider font-semibold block mb-1.5">
              Quick Suggestions
            </span>
            <div className="flex flex-wrap gap-1.5">
              {PRESET_REASONS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setReason(preset)}
                  className="text-[11px] bg-surface-subtle hover:bg-surface-border text-ink-primary border border-surface-border px-2.5 py-1 rounded-lg transition text-left"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-divider">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isRejecting}
            className="text-xs min-h-10 px-4"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleReject}
            disabled={isRejecting || !isReasonValid}
            className="text-xs min-h-10 px-4 gap-2 bg-status-rejected-text hover:opacity-90"
          >
            <XCircle className={`h-4 w-4 ${isRejecting ? 'animate-spin' : ''}`} />
            <span>{isRejecting ? 'Rejecting Action...' : 'Confirm Rejection'}</span>
          </Button>
        </div>
      </div>
    </div>
  )
}
