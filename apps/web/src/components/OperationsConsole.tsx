import { useState, useMemo, FC } from 'react'
import {
  SupportCaseItem,
  CaseDetail,
  VerificationResult,
} from '../types/api'
import { SourceBadge } from './SourceBadge'
import { ApprovalModal } from './ApprovalModal'
import { RejectModal } from './RejectModal'
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Play,
  Sparkles,
  ArrowUpRight,
  Filter,
  Search,
  Clock,
  User,
  History,
  Layers,
  ChevronRight,
  FileText,
} from 'lucide-react'

interface OperationsConsoleProps {
  cases: SupportCaseItem[]
  onApproveCase: (caseId: string, version: number, actionHash: string) => Promise<void>
  onRejectCase: (
    caseId: string,
    version: number,
    actionHash: string,
    reason: string
  ) => Promise<void>
  onAssignCase: (caseId: string, version: number, queue: string) => Promise<void>
  onSimulateSettlement: () => Promise<void>
  onVerifyCase: (caseId: string) => Promise<void>
  isSimulating: boolean
  verificationResult: VerificationResult | null
  activeCaseDetail: CaseDetail | null
  onSelectCase: (caseId: string) => void
  isLoadingDetail?: boolean
}

const QUEUES = [
  { id: 'ALL', label: 'All Queues' },
  { id: 'SETTLEMENT_OPS', label: 'Settlement Ops' },
  { id: 'SETTLEMENTS', label: 'Settlements' },
  { id: 'TECH_SUPPORT', label: 'Tech Support' },
  { id: 'ESCALATIONS', label: 'Escalations' },
]

const STATUSES = [
  'ALL',
  'AWAITING_APPROVAL',
  'NEW',
  'IN_PROGRESS',
  'VERIFYING',
  'APPROVED',
  'REJECTED',
  'RESOLVED',
]

export const OperationsConsole: FC<OperationsConsoleProps> = ({
  cases,
  onApproveCase,
  onRejectCase,
  onAssignCase,
  onSimulateSettlement,
  onVerifyCase,
  isSimulating,
  verificationResult,
  activeCaseDetail,
  onSelectCase,
  isLoadingDetail = false,
}) => {
  const [selectedQueue, setSelectedQueue] = useState('ALL')
  const [selectedStatus, setSelectedStatus] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [targetAssignQueue, setTargetAssignQueue] = useState('SETTLEMENT_OPS')

  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false)
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [isRejecting, setIsRejecting] = useState(false)
  const [isAssigning, setIsAssigning] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)

  // Compute queue counts
  const queueCounts = useMemo(() => {
    const counts: Record<string, number> = { ALL: cases.length }
    QUEUES.slice(1).forEach((q) => {
      counts[q.id] = cases.filter((c) => c.queue === q.id).length
    })
    return counts
  }, [cases])

  // Filter cases
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      if (selectedQueue !== 'ALL' && c.queue !== selectedQueue) return false
      if (selectedStatus !== 'ALL' && c.status !== selectedStatus) return false
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase()
        const matchNumber = c.case_number.toLowerCase().includes(query)
        const matchSummary = c.summary.toLowerCase().includes(query)
        if (!matchNumber && !matchSummary) return false
      }
      return true
    })
  }, [cases, selectedQueue, selectedStatus, searchQuery])

  // Selected case item
  const selectedCase =
    cases.find((c) => c.id === activeCaseDetail?.id) ||
    filteredCases[0] ||
    cases[0] ||
    null

  const handleApproveConfirm = async (
    caseId: string,
    version: number,
    actionHash: string
  ) => {
    try {
      setIsApproving(true)
      await onApproveCase(caseId, version, actionHash)
    } finally {
      setIsApproving(false)
    }
  }

  const handleRejectConfirm = async (
    caseId: string,
    version: number,
    actionHash: string,
    reason: string
  ) => {
    try {
      setIsRejecting(true)
      await onRejectCase(caseId, version, actionHash, reason)
    } finally {
      setIsRejecting(false)
    }
  }

  const handleAssign = async () => {
    if (!selectedCase) return
    try {
      setIsAssigning(true)
      await onAssignCase(selectedCase.id, selectedCase.version, targetAssignQueue)
    } finally {
      setIsAssigning(false)
    }
  }

  const handleEscalate = async () => {
    if (!selectedCase) return
    try {
      setIsAssigning(true)
      await onAssignCase(selectedCase.id, selectedCase.version, 'ESCALATIONS')
    } finally {
      setIsAssigning(false)
    }
  }

  const handleVerify = async () => {
    if (!selectedCase) return
    try {
      setIsVerifying(true)
      await onVerifyCase(selectedCase.id)
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Console Header Bar */}
      <div className="p-6 bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">Operations Support Console</h2>
            <span className="text-[10px] font-bold uppercase bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2.5 py-0.5 rounded-full">
              SUPPORT AGENT / SUPERVISOR
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Gated Human Approvals, Queue Management, Independent Verification, and Ledger Simulation
          </p>
        </div>

        {/* Bank Simulation Trigger */}
        <div className="flex items-center gap-3">
          <button
            onClick={onSimulateSettlement}
            disabled={isSimulating}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 px-4 py-2.5 rounded-xl font-bold text-xs shadow-lg shadow-emerald-500/20 transition disabled:opacity-50"
            title="Audited demo step: insert missing ₹6,000 ledger entry with source_type='SYNTHETIC_DEMO'"
          >
            <Play className={`h-4 w-4 ${isSimulating ? 'animate-spin' : ''}`} />
            <span>{isSimulating ? 'Simulating Credit...' : 'Simulate Bank Settlement (₹6,000)'}</span>
            <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 bg-slate-950/20 rounded font-black">
              DEMO
            </span>
          </button>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="p-4 bg-slate-900/70 rounded-2xl border border-slate-800 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Queue Filter Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
            {QUEUES.map((q) => {
              const count = queueCounts[q.id] || 0
              const isSelected = selectedQueue === q.id
              return (
                <button
                  key={q.id}
                  onClick={() => setSelectedQueue(q.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition ${
                    isSelected
                      ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20 font-semibold'
                      : 'bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>{q.label}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                      isSelected ? 'bg-purple-800/60 text-purple-200' : 'bg-slate-700/60 text-slate-400'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Search Input */}
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 w-full md:w-64">
            <Search className="h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Filter by case number or summary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent outline-none text-xs w-full placeholder:text-slate-500"
            />
          </div>
        </div>

        {/* Status Filter Row */}
        <div className="flex items-center gap-2 pt-2 border-t border-slate-800/60 text-xs text-slate-400 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-500">
            <Filter className="h-3 w-3" /> Status:
          </span>
          {STATUSES.map((status) => (
            <button
              key={status}
              onClick={() => setSelectedStatus(status)}
              className={`px-2 py-0.5 rounded-lg text-[11px] font-medium transition ${
                selectedStatus === status
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Main Workspace: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Queue List (4 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400 pb-1">
            <span className="font-bold text-white flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-purple-400" /> Support Cases Queue
            </span>
            <span>
              {filteredCases.length} of {cases.length} cases
            </span>
          </div>

          <div className="space-y-2.5 max-h-[720px] overflow-y-auto pr-1">
            {filteredCases.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800 text-xs space-y-1">
                <FileText className="h-8 w-8 mx-auto text-slate-600 mb-2 opacity-50" />
                <p className="font-semibold text-slate-400">No matching cases found</p>
                <p className="text-[11px]">Adjust queue or status filters to view cases</p>
              </div>
            ) : (
              filteredCases.map((sc) => {
                const isSelected = selectedCase?.id === sc.id
                const isAwaitingApproval = sc.status === 'AWAITING_APPROVAL'

                return (
                  <div
                    key={sc.id}
                    onClick={() => onSelectCase(sc.id)}
                    className={`p-3.5 rounded-2xl border text-xs cursor-pointer transition ${
                      isSelected
                        ? 'bg-purple-950/40 border-purple-500/80 text-white shadow-lg shadow-purple-950/40 ring-1 ring-purple-500/40'
                        : 'bg-slate-900/70 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-purple-400">
                          {sc.case_number}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-slate-800 text-slate-400 font-mono">
                          v{sc.version}
                        </span>
                      </div>

                      {/* Status Badge */}
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                          isAwaitingApproval
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                            : sc.status === 'APPROVED'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : sc.status === 'VERIFYING'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : sc.status === 'RESOLVED'
                            ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                            : sc.status === 'REJECTED'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {sc.status}
                      </span>
                    </div>

                    <p className="mt-1.5 line-clamp-2 text-slate-300 font-normal leading-relaxed">
                      {sc.summary}
                    </p>

                    <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span className="flex items-center gap-1">
                        Queue: <strong className="text-slate-300 font-sans">{sc.queue}</strong>
                      </span>
                      <span className="text-slate-500">
                        {new Date(sc.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    {isAwaitingApproval && (
                      <div className="mt-2 py-1 px-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-[10px] font-semibold text-amber-300 flex items-center gap-1.5">
                        <ShieldAlert className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                        <span>Action Approval Required (&gt; ₹5,000 threshold)</span>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Right Column: Selected Case Details & Actions (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {selectedCase ? (
            <>
              {/* Selected Case Header */}
              <div className="p-5 bg-slate-900/80 rounded-2xl border border-slate-800 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-white font-mono">
                        {selectedCase.case_number}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-slate-800 text-purple-300">
                        Version {selectedCase.version}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                        {selectedCase.priority}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 font-medium">{selectedCase.summary}</p>
                  </div>

                  <div className="text-right text-[11px] text-slate-400 font-mono">
                    <div>
                      Queue: <strong className="text-purple-400 font-sans">{selectedCase.queue}</strong>
                    </div>
                    <div>
                      Status: <strong className="text-white font-sans">{selectedCase.status}</strong>
                    </div>
                  </div>
                </div>

                {/* Queue Re-assignment and Actions Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-slate-400">Assign Queue:</span>
                    <select
                      value={targetAssignQueue}
                      onChange={(e) => setTargetAssignQueue(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 outline-none cursor-pointer"
                    >
                      <option value="SETTLEMENT_OPS">Settlement Ops</option>
                      <option value="SETTLEMENTS">Settlements</option>
                      <option value="TECH_SUPPORT">Tech Support</option>
                    </select>
                    <button
                      onClick={handleAssign}
                      disabled={isAssigning}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-xl font-medium transition disabled:opacity-50"
                    >
                      {isAssigning ? 'Updating...' : 'Assign'}
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleEscalate}
                      disabled={isAssigning || selectedCase.queue === 'ESCALATIONS'}
                      className="inline-flex items-center gap-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 text-xs px-3 py-1.5 rounded-xl font-semibold transition disabled:opacity-40"
                      title="Escalate case to Tier 2 Escalations queue"
                    >
                      <ArrowUpRight className="h-3.5 w-3.5 text-rose-400" />
                      <span>{selectedCase.queue === 'ESCALATIONS' ? 'Escalated' : 'Escalate'}</span>
                    </button>

                    <button
                      onClick={handleVerify}
                      disabled={isVerifying}
                      className="inline-flex items-center gap-1.5 bg-sky-950/40 hover:bg-sky-900/60 text-sky-400 border border-sky-800/60 text-xs px-3 py-1.5 rounded-xl font-semibold transition disabled:opacity-50"
                      title="Run independent verification against ledger"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-sky-400" />
                      <span>{isVerifying ? 'Verifying...' : 'Verify Resolution'}</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Action Approval Card (when awaiting approval) */}
              {selectedCase.status === 'AWAITING_APPROVAL' && (
                <div className="p-6 bg-slate-900/90 rounded-2xl border border-amber-500/40 space-y-4 shadow-xl ring-1 ring-amber-500/20">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      <ShieldAlert className="h-5 w-5 text-amber-400" />
                      <h3 className="font-bold text-sm text-white">
                        Action Approval Required: Settlement Re-Sync
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                      POLICY GATE: &gt; ₹5,000.00
                    </span>
                  </div>

                  <div className="text-xs text-slate-300 space-y-2.5">
                    <p className="leading-relaxed">
                      OpsSaathi detected an overdue settlement discrepancy of{' '}
                      <strong className="text-amber-400 font-bold">₹6,000.00</strong>. Per Policy Rule
                      #3, automated settlement re-sync requests exceeding ₹5,000.00 require human
                      supervisor authorization.
                    </p>

                    <div className="p-3 bg-slate-950/90 rounded-xl border border-slate-800 font-mono text-[11px] grid grid-cols-2 gap-2">
                      <div>
                        <span className="text-slate-500">Case ID:</span>{' '}
                        <span className="text-slate-300">{selectedCase.id}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Case Version:</span>{' '}
                        <span className="text-purple-400 font-bold">v{selectedCase.version}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Action:</span>{' '}
                        <span className="text-slate-200">SETTLEMENT_RESYNC</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Adapter Target:</span>{' '}
                        <SourceBadge source="MOCK_SETTLEMENT_OPS" size="sm" />
                      </div>
                    </div>
                  </div>

                  {/* Approve / Reject Trigger Buttons */}
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => setIsApprovalModalOpen(true)}
                      className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition shadow-lg shadow-emerald-600/20"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Review &amp; Approve Action</span>
                    </button>

                    <button
                      onClick={() => setIsRejectModalOpen(true)}
                      className="flex-1 flex items-center justify-center gap-2 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 font-semibold py-2.5 px-4 rounded-xl text-xs transition"
                    >
                      <XCircle className="h-4 w-4" />
                      <span>Reject Action</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Independent Verification Report Card */}
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
                      <div>Expected: ₹{verificationResult.expected_net || '15000.00'}</div>
                      <div>Observed: ₹{verificationResult.before_observed || '9000.00'}</div>
                      <div className="text-rose-400 font-bold">
                        Discrepancy: ₹
                        {(
                          Number(verificationResult.expected_net || 15000) -
                          Number(verificationResult.before_observed || 9000)
                        ).toFixed(2)}
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                      <span className="text-slate-500 font-sans font-semibold">After Fresh Read:</span>
                      <div>Expected: ₹{verificationResult.expected_net || '15000.00'}</div>
                      <div>Observed: ₹{verificationResult.after_observed || '15000.00'}</div>
                      <div className="text-emerald-400 font-bold">
                        Discrepancy: ₹
                        {(
                          Number(verificationResult.expected_net || 15000) -
                          Number(verificationResult.after_observed || 15000)
                        ).toFixed(2)}
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-300 text-center text-xs font-sans font-semibold">
                    Verdict: {verificationResult.verification_result} (Ledger match confirmed via
                    read-only verifier session)
                  </div>
                </div>
              )}

              {/* Case Audit Timeline */}
              <div className="p-5 bg-slate-900/70 rounded-2xl border border-slate-800 space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <History className="h-4 w-4 text-purple-400" />
                    <h3 className="font-bold text-xs text-white">Case Audit Timeline</h3>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    {activeCaseDetail?.timeline?.length || 0} Events Recorded
                  </span>
                </div>

                {isLoadingDetail ? (
                  <div className="py-8 text-center text-slate-500 text-xs">
                    Loading audit events...
                  </div>
                ) : !activeCaseDetail?.timeline || activeCaseDetail.timeline.length === 0 ? (
                  <div className="py-8 text-center text-slate-500 text-xs">
                    No timeline events recorded yet.
                  </div>
                ) : (
                  <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
                    {activeCaseDetail.timeline.map((ev) => {
                      const isInternal = ev.visibility === 'INTERNAL'

                      return (
                        <div key={ev.id} className="relative flex items-start gap-3 pl-1 text-xs">
                          {/* Dot */}
                          <div
                            className={`h-6 w-6 rounded-full flex items-center justify-center shrink-0 border z-10 ${
                              ev.event_type === 'APPROVAL_GRANTED'
                                ? 'bg-emerald-950 border-emerald-500 text-emerald-400'
                                : ev.event_type === 'APPROVAL_REJECTED'
                                ? 'bg-rose-950 border-rose-500 text-rose-400'
                                : ev.event_type === 'APPROVAL_REQUESTED'
                                ? 'bg-amber-950 border-amber-500 text-amber-400'
                                : 'bg-slate-900 border-slate-700 text-slate-400'
                            }`}
                          >
                            <ChevronRight className="h-3 w-3" />
                          </div>

                          {/* Event Body */}
                          <div className="flex-1 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-bold text-purple-300">
                                {ev.event_type}
                              </span>
                              <div className="flex items-center gap-2">
                                <span
                                  className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded ${
                                    isInternal
                                      ? 'bg-purple-950 text-purple-400 border border-purple-800'
                                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                  }`}
                                >
                                  {ev.visibility}
                                </span>
                                <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {new Date(ev.created_at).toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    second: '2-digit',
                                  })}
                                </span>
                              </div>
                            </div>

                            <div className="text-[11px] text-slate-400 flex items-center gap-1">
                              <User className="h-3 w-3 text-slate-500" />
                              <span>Actor:</span>
                              <strong className="text-slate-300 font-medium">{ev.actor}</strong>
                            </div>

                            {/* Payload Details */}
                            {ev.payload && Object.keys(ev.payload).length > 0 && (
                              <div className="mt-1 pt-1.5 border-t border-slate-900 font-mono text-[10px] text-slate-400 bg-slate-900/60 p-2 rounded-lg">
                                {Object.entries(ev.payload).map(([k, v]) => (
                                  <div key={k} className="truncate">
                                    <span className="text-slate-500">{k}:</span>{' '}
                                    <span className="text-slate-300">
                                      {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-16 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800 text-xs space-y-2">
              <FileText className="h-10 w-10 mx-auto text-slate-600 opacity-40 mb-2" />
              <p className="font-semibold text-slate-300 text-sm">Select a case from the queue</p>
              <p className="text-slate-500 max-w-sm mx-auto">
                Select any support case in the queue list to review its evidence, gated actions, and
                tamper-evident audit events.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Approval Modal */}
      <ApprovalModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        caseItem={selectedCase}
        pendingApproval={activeCaseDetail?.pending_approval || null}
        onConfirmApprove={handleApproveConfirm}
        isApproving={isApproving}
      />

      {/* Reject Modal */}
      <RejectModal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        caseItem={selectedCase}
        pendingApproval={activeCaseDetail?.pending_approval || null}
        onConfirmReject={handleRejectConfirm}
        isRejecting={isRejecting}
      />
    </div>
  )
}
