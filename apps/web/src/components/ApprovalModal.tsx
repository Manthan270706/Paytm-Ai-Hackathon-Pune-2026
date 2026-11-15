import { FC } from 'react'
import { SupportCaseItem, ApprovalSummary } from '../types/api'
import { SourceBadge } from './SourceBadge'
import { ShieldCheck, X, AlertTriangle, CheckCircle2, Lock } from 'lucide-react'
import { Button } from './Button'

interface ApprovalModalProps {
  isOpen: boolean
  onClose: () => void
  caseItem: SupportCaseItem | null
  pendingApproval: ApprovalSummary | null
  discrepancyAmount?: string
  onConfirmApprove: (caseId: string, version: number, actionHash: string) => Promise<void>
  isApproving: boolean
}

export const ApprovalModal: FC<ApprovalModalProps> = ({
  isOpen,
  onClose,
  caseItem,
  pendingApproval,
  discrepancyAmount,
  onConfirmApprove,
  isApproving,
}) => {
  if (!isOpen || !caseItem) return null

  const actionHash =
    pendingApproval?.action_hash ||
    '44efa879046efa3a441c61673e778f5ed3cb2adec16c9d57ca0f88b6139a2e02'

  const formattedDiscrepancy = discrepancyAmount || '6,000.00'

  const handleApprove = async () => {
    await onConfirmApprove(caseItem.id, caseItem.version, actionHash)
    onClose()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="approval-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/50 backdrop-blur-sm animate-in fade-in duration-200 font-sans"
    >
      <div className="bg-surface-card border border-surface-border rounded-2xl max-w-xl w-full p-6 shadow-xl space-y-5 text-ink-primary">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-surface-divider pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-status-approval-bg border border-status-approval-border text-status-approval-text">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h3 id="approval-modal-title" className="text-base font-bold text-paytm-navy tracking-tight">
                Authorize Gated Action
              </h3>
              <p className="text-xs text-ink-secondary">
                Human Supervisor Authorization (Two-key discipline)
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isApproving}
            aria-label="Close dialog"
            className="flex items-center justify-center w-10 h-10 min-h-12 min-w-12 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-surface-subtle transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Policy Trigger Banner */}
        <div className="p-3 bg-status-approval-bg border border-status-approval-border rounded-xl text-xs flex items-start gap-2.5 text-status-approval-text">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Policy Gate Triggered: </span>
            The autonomous agent computed an operational action ({pendingApproval?.action || 'SETTLEMENT_RESYNC'}) with value ₹{formattedDiscrepancy}. Automated actions exceeding ₹5,000 require explicit supervisor sign-off.
          </div>
        </div>

        {/* Action Details & Discrepancy Evidence */}
        <div className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border space-y-1">
              <span className="text-[10px] uppercase font-bold text-ink-secondary tracking-wider">
                Action Type
              </span>
              <div className="font-mono font-bold text-paytm-navy text-sm">
                {pendingApproval?.action || 'SETTLEMENT_RESYNC'}
              </div>
              <div className="text-[11px] text-ink-secondary flex items-center gap-1.5 mt-1">
                <span>Target:</span>
                <SourceBadge
                  source={
                    caseItem.queue === 'TECH_SUPPORT'
                      ? 'MOCK_HARDWARE_IOT'
                      : caseItem.queue === 'ESCALATIONS'
                      ? 'MOCK_BANK_IMPS'
                      : 'MOCK_SETTLEMENT_OPS'
                  }
                  size="sm"
                />
              </div>
            </div>

            <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border space-y-1">
              <span className="text-[10px] uppercase font-bold text-ink-secondary tracking-wider">
                Discrepancy Value
              </span>
              <div className="font-mono font-bold text-status-approval-text text-sm">
                ₹{formattedDiscrepancy}
              </div>
              <div className="text-[11px] text-ink-secondary mt-1">
                Status: <span className="font-semibold text-paytm-navy">{caseItem.status}</span>
              </div>
            </div>
          </div>

          {/* Canonical Action Payload / Fingerprint */}
          <div className="p-3 bg-surface-canvas rounded-xl border border-surface-border font-mono text-[11px] space-y-1.5">
            <div className="flex items-center justify-between text-ink-secondary pb-1 border-b border-surface-divider">
              <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold">
                <Lock className="h-3 w-3 text-paytm-navy" /> Tamper-Proof Resume Contract
              </span>
              <span className="text-paytm-navy font-semibold">Case v{caseItem.version}</span>
            </div>
            <div className="flex items-center justify-between text-ink-secondary">
              <span>Case Number:</span>
              <span className="text-ink-primary font-medium">{caseItem.case_number}</span>
            </div>
            <div>
              <span className="text-ink-secondary">SHA-256 Action Hash:</span>
              <div className="mt-0.5 p-1.5 bg-surface-card rounded border border-surface-border text-[10px] text-paytm-navy break-all select-all font-mono">
                {actionHash}
              </div>
            </div>
          </div>

          <p className="text-[11px] text-ink-muted italic">
            Authorizing this action will verify the action hash, assert optimistic case version concurrency, and dispatch an idempotent re-sync to Settlement Operations.
          </p>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-divider">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isApproving}
            className="text-xs min-h-10 px-4"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleApprove}
            disabled={isApproving}
            className="text-xs min-h-10 px-4 gap-2"
          >
            <CheckCircle2 className={`h-4 w-4 ${isApproving ? 'animate-spin' : ''}`} />
            <span>{isApproving ? 'Resuming Action...' : `Confirm & Authorize ${pendingApproval?.action || 'Action'}`}</span>
          </Button>
        </div>
      </div>
    </div>
  )
}
