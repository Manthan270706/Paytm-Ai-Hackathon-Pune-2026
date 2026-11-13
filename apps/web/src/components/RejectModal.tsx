import { useState, FC } from 'react'
import { SupportCaseItem, ApprovalSummary } from '../types/api'
import { XCircle, X, AlertCircle } from 'lucide-react'

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 text-slate-200">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <XCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Reject Gated Action</h3>
              <p className="text-xs text-slate-400">
                Settlement Re-Sync Rejection (Case {caseItem.case_number})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isRejecting}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Warning info */}
        <div className="p-3 bg-rose-950/40 border border-rose-800/50 rounded-xl text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
          <div>
            Rejecting this action cancels the pending automated settlement re-sync. An immutable
            audit event with your documented justification will be written to the case timeline.
          </div>
        </div>

        {/* Rejection Reason Form */}
        <div className="space-y-2 text-xs">
          <label className="block font-semibold text-slate-300">
            Rejection Reason <span className="text-rose-400">*</span>
            <span className="text-slate-500 font-normal ml-1">
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
            className={`w-full p-3 bg-slate-950 rounded-xl border text-xs text-slate-200 placeholder:text-slate-500 outline-none transition ${
              hasAttemptedSubmit && !isReasonValid
                ? 'border-rose-500 focus:border-rose-400'
                : 'border-slate-800 focus:border-rose-500/60'
            }`}
          />
          {hasAttemptedSubmit && !isReasonValid && (
            <p className="text-[11px] text-rose-400 font-medium">
              Please enter a rejection reason before confirming.
            </p>
          )}

          {/* Quick presets */}
          <div className="pt-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block mb-1.5">
              Quick Suggestions
            </span>
            <div className="flex flex-wrap gap-1.5">
              {PRESET_REASONS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setReason(preset)}
                  className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 px-2 py-1 rounded-lg transition text-left"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            disabled={isRejecting}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleReject}
            disabled={isRejecting || !isReasonValid}
            className="inline-flex items-center gap-2 bg-rose-600 hover:bg-rose-500 disabled:bg-rose-950 disabled:text-rose-500 text-white px-5 py-2.5 rounded-xl font-semibold text-xs transition shadow-lg shadow-rose-600/20 disabled:cursor-not-allowed"
          >
            <XCircle className={`h-4 w-4 ${isRejecting ? 'animate-spin' : ''}`} />
            <span>{isRejecting ? 'Rejecting Action...' : 'Confirm Rejection'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
