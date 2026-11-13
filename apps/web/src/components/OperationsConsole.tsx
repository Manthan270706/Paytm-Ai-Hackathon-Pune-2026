import { useState, FC } from 'react'
import { SupportCaseItem } from '../types/api'
import { SourceBadge } from './SourceBadge'
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Play,
  Sparkles,
} from 'lucide-react'

interface OperationsConsoleProps {
  cases: SupportCaseItem[]
  onApproveCase: (caseId: string, version: number) => void
  onRejectCase: (caseId: string, version: number) => void
  onSimulateSettlement: () => void
  onVerifyCase: (caseId: string) => void
  isSimulating: boolean
  verificationResult: any | null
}

export const OperationsConsole: FC<OperationsConsoleProps> = ({
  cases,
  onApproveCase,
  onRejectCase,
  onSimulateSettlement,
  onVerifyCase,
  isSimulating,
  verificationResult,
}) => {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(
    cases.length > 0 ? cases[0].id : null
  )

  const selectedCase = cases.find((c) => c.id === selectedCaseId) || cases[0]

  return (
    <div className="space-y-6">
      {/* Console Header */}
      <div className="p-6 bg-slate-800/80 rounded-2xl border border-slate-700/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">Operations Support Console</h2>
            <span className="text-[10px] font-bold uppercase bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full">
              SUPPORT AGENT / SUPERVISOR
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Gated Human Approvals, Verification Auditing, and Bank Settlement Simulation
          </p>
        </div>

        {/* Bank Simulation Trigger */}
        <button
          onClick={onSimulateSettlement}
          disabled={isSimulating}
          className="inline-flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 px-4 py-2.5 rounded-xl font-semibold text-xs shadow-lg shadow-emerald-500/20 transition disabled:opacity-50"
          title="Demo step: simulate bank settlement ledger credit of ₹6,000"
        >
          <Play className={`h-4 w-4 ${isSimulating ? 'animate-spin' : ''}`} />
          <span>{isSimulating ? 'Simulating...' : 'Simulate Bank Settlement (₹6,000)'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Case Queue List */}
        <div className="p-5 bg-slate-800/60 rounded-2xl border border-slate-700/60 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-700/60">
            <span className="font-bold text-white">Pending Approval Queue</span>
            <span>{cases.length} active</span>
          </div>

          <div className="space-y-2">
            {cases.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">No active cases found</div>
            ) : (
              cases.map((sc) => {
                const isSelected = selectedCase?.id === sc.id
                return (
                  <div
                    key={sc.id}
                    onClick={() => setSelectedCaseId(sc.id)}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                      isSelected
                        ? 'bg-purple-950/40 border-purple-500/60 text-white shadow-md'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-purple-400">{sc.case_number}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-slate-800 text-slate-400">
                        v{sc.version}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-1 text-slate-300">{sc.summary}</p>
                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>Status: {sc.status}</span>
                      <span>Queue: {sc.queue}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Selected Case Inspection & Approval Panel */}
        <div className="lg:col-span-2 space-y-6">
          {selectedCase ? (
            <>
              {/* Approval Action Card */}
              <div className="p-6 bg-slate-800/60 rounded-2xl border border-slate-700/60 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-5 w-5 text-amber-400" />
                    <h3 className="font-bold text-sm text-white">
                      Action Approval Required: Settlement Re-Sync
                    </h3>
                  </div>
                  <span className="text-xs font-mono font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                    POLICY GATE: &gt; ₹5,000.00
                  </span>
                </div>

                <div className="text-xs text-slate-300 space-y-2">
                  <p>
                    The OpsSaathi agent detected an overdue discrepancy of <strong className="text-amber-400">₹6,000.00</strong>.
                    Per Policy Rule #3, automated settlement re-sync requests exceeding ₹5,000.00 require human supervisor authorization.
                  </p>

                  <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 font-mono text-[11px] grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-slate-500">Case ID:</span>{' '}
                      <span className="text-slate-300">{selectedCase.id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Case Version:</span>{' '}
                      <span className="text-purple-400 font-bold">{selectedCase.version}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Action Hash:</span>{' '}
                      <span className="text-slate-400">hash_resync_batch_01</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Adapter Target:</span>{' '}
                      <SourceBadge source="MOCK_SETTLEMENT_OPS" size="sm" />
                    </div>
                  </div>
                </div>

                {/* Approve / Reject Buttons */}
                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={() => onApproveCase(selectedCase.id, selectedCase.version)}
                    className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition shadow-md shadow-emerald-600/20"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Approve Settlement Re-Sync</span>
                  </button>

                  <button
                    onClick={() => onRejectCase(selectedCase.id, selectedCase.version)}
                    className="flex-1 flex items-center justify-center gap-2 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 font-semibold py-2.5 px-4 rounded-xl text-xs transition"
                  >
                    <XCircle className="h-4 w-4" />
                    <span>Reject Action</span>
                  </button>

                  <button
                    onClick={() => onVerifyCase(selectedCase.id)}
                    className="flex items-center gap-2 bg-sky-950/40 hover:bg-sky-900/60 text-sky-400 border border-sky-800/60 font-semibold py-2.5 px-4 rounded-xl text-xs transition"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>Verify Resolution</span>
                  </button>
                </div>
              </div>

              {/* Independent Verification Diff Card */}
              {verificationResult && (
                <div className="p-5 bg-slate-900/90 rounded-2xl border border-sky-500/30 space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <span className="font-sans font-bold text-sky-400 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      Independent Verification Report (Trust Rule 5 &amp; 6)
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Role: {verificationResult.verifier_role || 'opssaathi_verifier'} (READ-ONLY)
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-[11px]">
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                      <span className="text-slate-500 font-sans font-semibold">Before Simulation:</span>
                      <div>Expected: ₹15,000.00</div>
                      <div>Observed: ₹9,000.00</div>
                      <div className="text-rose-400 font-bold">Discrepancy: ₹6,000.00</div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                      <span className="text-slate-500 font-sans font-semibold">After Fresh Read:</span>
                      <div>Expected: ₹15,000.00</div>
                      <div>Observed: ₹15,000.00</div>
                      <div className="text-emerald-400 font-bold">Discrepancy: ₹0.00</div>
                    </div>
                  </div>

                  <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-300 text-center text-xs font-sans font-semibold">
                    Verdict: {verificationResult.verification_result} (Ledger match confirmed via read-only verifier role)
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-12 text-center text-slate-500 bg-slate-800/40 rounded-2xl border border-slate-700/40 text-xs">
              Select a support case from the queue to view approval details.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
