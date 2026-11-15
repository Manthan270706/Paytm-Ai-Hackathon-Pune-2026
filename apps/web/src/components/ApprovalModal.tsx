import { FC } from 'react'
import { SupportCaseItem, ApprovalSummary } from '../types/api'
import { SourceBadge } from './SourceBadge'
import { ShieldCheck, X, AlertTriangle, CheckCircle2, Lock } from 'lucide-react'

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5 text-slate-200">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Authorize Gated Action
              </h3>
              <p className="text-xs text-slate-400">
                Human Supervisor Authorization (Policy Rule #3 &amp; PRD §5.3)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isApproving}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Policy Trigger Banner */}
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs flex items-start gap-2.5 text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <span className="font-semibold text-amber-200">Policy Gate Triggered: </span>
            The autonomous agent computed an operational action ({pendingApproval?.action || 'SETTLEMENT_RESYNC'}) with value ₹{formattedDiscrepancy}. Per Policy Rule
            #3, automated actions exceeding the ₹5,000 threshold require explicit human supervisor authorization.
          </div>
        </div>

        {/* Action Details & Discrepancy Evidence */}
        <div className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                Action Type
              </span>
              <div className="font-mono font-bold text-purple-400 text-sm">
                {pendingApproval?.action || 'SETTLEMENT_RESYNC'}
              </div>
              <div className="text-[11px] text-slate-400 flex items-center gap-1.5 mt-1">
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

            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                Amount / Discrepancy
              </span>
              <div className="font-mono font-bold text-amber-400 text-sm">₹{formattedDiscrepancy}</div>
              <div className="text-[11px] text-slate-400 mt-1">
                Status: <span className="text-amber-400 font-semibold">{caseItem.status}</span>
              </div>
            </div>
          </div>

          {/* Canonical Action Payload / Fingerprint */}
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 font-mono text-[11px] space-y-1.5">
            <div className="flex items-center justify-between text-slate-400 pb-1 border-b border-slate-800">
              <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold">
                <Lock className="h-3 w-3 text-sky-400" /> Tamper-Proof Resume Contract
              </span>
              <span className="text-purple-400 font-semibold">Case v{caseItem.version}</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Case Number:</span>
              <span className="text-slate-200">{caseItem.case_number}</span>
            </div>
            <div>
              <span className="text-slate-400">SHA-256 Action Hash:</span>
              <div className="mt-0.5 p-1.5 bg-slate-900 rounded border border-slate-800 text-[10px] text-sky-300 break-all select-all font-mono">
                {actionHash}
              </div>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 italic">
            Resuming this action will verify the action hash, assert optimistic case version,
            dispatch an idempotent re-sync to Settlement Operations, and advance the case to
            verifying.
          </p>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            disabled={isApproving}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={isApproving}
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-xl font-semibold text-xs transition shadow-lg shadow-emerald-600/25 disabled:opacity-50"
          >
            <CheckCircle2 className={`h-4 w-4 ${isApproving ? 'animate-spin' : ''}`} />
            <span>{isApproving ? 'Resuming Action...' : `Confirm & Authorize ${pendingApproval?.action || 'Action'}`}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
