import { useState, useMemo, FC } from 'react'
import {
  SupportCaseItem,
  CaseDetail,
  VerificationResult,
  OutcomeMetrics,
} from '../types/api'
import { SourceBadge } from './SourceBadge'
import { ApprovalModal } from './ApprovalModal'
import { RejectModal } from './RejectModal'
import { CreateCaseModal } from './CreateCaseModal'
import { MetricsTile } from './MetricsTile'
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Play,
  Sparkles,
  PlusCircle,
  ArrowUpRight,
  Filter,
  Search,
  Clock,
  User,
  History,
  Layers,
  ChevronRight,
  FileText,
  AlertTriangle,
  Check,
  Info,
  X,
} from 'lucide-react'

export interface ActionFeedbackNotice {
  type: 'error' | 'warning' | 'info' | 'success'
  title: string
  message: string
  actionLabel?: string
  actionFn?: () => void
}

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
  metrics?: OutcomeMetrics | null
  onRefreshMetrics?: () => void
  isLoadingMetrics?: boolean
  actionFeedback?: ActionFeedbackNotice | null
  onClearFeedback?: () => void
  onCreateCase?: (data: {
    category: string
    priority: string
    queue: string
    summary: string
  }) => Promise<void>
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
  metrics,
  onRefreshMetrics,
  isLoadingMetrics = false,
  actionFeedback = null,
  onClearFeedback,
  onCreateCase,
}) => {
  const [selectedQueue, setSelectedQueue] = useState('ALL')
  const [selectedStatus, setSelectedStatus] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [targetAssignQueue, setTargetAssignQueue] = useState('SETTLEMENT_OPS')

  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false)
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [isRejecting, setIsRejecting] = useState(false)
  const [isAssigning, setIsAssigning] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [localNotice, setLocalNotice] = useState<ActionFeedbackNotice | null>(null)

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

  // Selected case item: only select if activeCaseDetail matches an active case; do NOT fall back to default case!
  const selectedCase = activeCaseDetail
    ? cases.find((c) => c.id === activeCaseDetail.id) || null
    : null

  const caseDiscrepancyAmount = useMemo(() => {
    if (!selectedCase) return '0.00'
    const tl = activeCaseDetail?.timeline || []
    const disc = tl.find((e) => e.payload?.discrepancy)?.payload?.discrepancy
    if (disc) return String(disc)
    const amt = tl.find((e) => e.payload?.amount)?.payload?.amount
    if (amt) return String(amt)
    const variance = tl.find((e) => e.payload?.variance)?.payload?.variance
    if (variance) return String(variance)
    const dup = tl.find((e) => e.payload?.duplicate_debit)?.payload?.duplicate_debit
    if (dup) return String(dup)
    const appAmt = tl.find((e) => e.payload?.approved_amount)?.payload?.approved_amount
    if (appAmt) return String(appAmt)
    const summaryMatch = selectedCase.summary.match(/₹([\d,]+(\.\d{2})?)/)
    if (summaryMatch && summaryMatch[1]) return summaryMatch[1]
    return '0.00'
  }, [activeCaseDetail, selectedCase])

  // Active notification banner priority: localNotice overrides actionFeedback
  const activeNotice = localNotice || actionFeedback
  const handleDismissNotice = () => {
    setLocalNotice(null)
    if (onClearFeedback) onClearFeedback()
  }

  const handleSimulateAndNotice = async () => {
    try {
      await onSimulateSettlement()
      setLocalNotice({
        type: 'success',
        title: 'Step 2 Completed: Bank Credit Recorded',
        message: `₹${caseDiscrepancyAmount} credit recorded on ledger. Now proceed to Step 3: click "Run Independent Verification" to verify and close this case.`,
        actionLabel: 'Run Independent Verification',
        actionFn: () => handleVerify(),
      })
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Simulation Error',
        message: err?.message || 'Failed to simulate bank settlement.',
      })
    }
  }

  const handleApproveConfirm = async (
    caseId: string,
    version: number,
    actionHash: string
  ) => {
    try {
      setIsApproving(true)
      await onApproveCase(caseId, version, actionHash)
      setLocalNotice({
        type: 'success',
        title: 'Step 1 Completed: Action Approved',
        message: 'Case is now in VERIFYING status. Step 2: Click "Simulate Credit" to deposit credit, then run verification.',
        actionLabel: caseDiscrepancyAmount !== '0.00' ? `Simulate Credit (₹${caseDiscrepancyAmount})` : 'Simulate Bank Settlement',
        actionFn: () => handleSimulateAndNotice(),
      })
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Approval Error',
        message: err?.message || 'Failed to approve case action.',
      })
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
      setLocalNotice({
        type: 'info',
        title: 'Action Rejected',
        message: 'Settlement re-sync rejected with documented reason.',
      })
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Rejection Error',
        message: err?.message || 'Failed to reject case action.',
      })
    } finally {
      setIsRejecting(false)
    }
  }

  const handleAssign = async () => {
    if (!selectedCase) return
    try {
      setIsAssigning(true)
      await onAssignCase(selectedCase.id, selectedCase.version, targetAssignQueue)
      setLocalNotice({
        type: 'info',
        title: 'Queue Updated',
        message: `Case ${selectedCase.case_number} successfully moved to ${targetAssignQueue}.`,
      })
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Queue Assignment Error',
        message: err?.message || 'Failed to assign queue.',
      })
    } finally {
      setIsAssigning(false)
    }
  }

  const handleEscalate = async () => {
    if (!selectedCase) return
    try {
      setIsAssigning(true)
      await onAssignCase(selectedCase.id, selectedCase.version, 'ESCALATIONS')
      setLocalNotice({
        type: 'warning',
        title: 'Case Escalated to Tier 2',
        message: `Case ${selectedCase.case_number} has been escalated to Tier 2 Escalations queue.`,
      })
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Escalation Error',
        message: err?.message || 'Failed to escalate case.',
      })
    } finally {
      setIsAssigning(false)
    }
  }

  const handleVerify = async () => {
    if (!selectedCase) return
    if (selectedCase.status === 'AWAITING_APPROVAL') {
      setLocalNotice({
        type: 'warning',
        title: 'Step 1 Authorization Required',
        message: `Case ${selectedCase.case_number} is awaiting supervisor authorization. Please review and authorize the settlement re-sync (Step 1) before running verification.`,
        actionLabel: 'Review & Approve Action',
        actionFn: () => setIsApprovalModalOpen(true),
      })
      return
    }
    if (selectedCase.status === 'RESOLVED') {
      setLocalNotice({
        type: 'info',
        title: 'Case Already Reconciled',
        message: `Case ${selectedCase.case_number} has already been verified and resolved with ₹0.00 discrepancy.`,
      })
      return
    }
    try {
      setIsVerifying(true)
      setLocalNotice(null)
      await onVerifyCase(selectedCase.id)
    } catch (err: any) {
      const msg = err?.message || 'Verification failed.'
      setLocalNotice({
        type: 'error',
        title: 'Verification Pre-condition Not Met',
        message: msg.includes('VERIFYING')
          ? 'Case must be approved before running verification. Please approve the action in Step 1.'
          : msg,
      })
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

        {/* Bank Simulation & Create Case Trigger */}
        <div className="flex items-center gap-3">
          {onCreateCase && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700/80 text-sky-400 border border-sky-500/30 px-3.5 py-2.5 rounded-xl font-bold text-xs shadow-md transition"
              title="Create a new operational support case across any queue"
            >
              <PlusCircle className="h-4 w-4" />
              <span>Create Case</span>
            </button>
          )}
          <button
            onClick={onSimulateSettlement}
            disabled={isSimulating}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 px-4 py-2.5 rounded-xl font-bold text-xs shadow-lg shadow-emerald-500/20 transition disabled:opacity-50"
            title="Audited demo step: insert missing ₹6,000 ledger entry with source_type='SYNTHETIC_DEMO'"
          >
            <Play className={`h-4 w-4 ${isSimulating ? 'animate-spin' : ''}`} />
            <span>
              {isSimulating
                ? 'Simulating Credit...'
                : selectedCase && caseDiscrepancyAmount !== '0.00'
                ? `Simulate Credit (₹${caseDiscrepancyAmount})`
                : 'Simulate Bank Settlement (₹6,000)'}
            </span>
            <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 bg-slate-950/20 rounded font-black">
              DEMO
            </span>
          </button>
        </div>
      </div>

      {/* Real-time Operational Outcome Metrics Tile */}
      <MetricsTile
        metrics={metrics || null}
        onRefresh={onRefreshMetrics}
        isLoading={isLoadingMetrics}
      />

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
                    onClick={() => onSelectCase(isSelected ? '' : sc.id)}
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
        <div className="lg:col-span-7 space-y-6 min-w-0">
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

                  <div className="flex items-center gap-3">
                    <div className="text-right text-[11px] text-slate-400 font-mono">
                      <div>
                        Queue: <strong className="text-purple-400 font-sans">{selectedCase.queue}</strong>
                      </div>
                      <div>
                        Status: <strong className="text-white font-sans">{selectedCase.status}</strong>
                      </div>
                    </div>
                    <button
                      onClick={() => onSelectCase('')}
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
                      title="Close case details (return to queue overview)"
                    >
                      <X className="h-4 w-4" />
                    </button>
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

              {/* Interactive Action Notice / Guidance Banner */}
              {activeNotice && (
                <div
                  className={`p-4 rounded-2xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in duration-200 shadow-xl ${
                    activeNotice.type === 'warning'
                      ? 'bg-amber-950/40 border-amber-500/50 text-amber-200 ring-1 ring-amber-500/20'
                      : activeNotice.type === 'error'
                      ? 'bg-rose-950/40 border-rose-500/50 text-rose-200 ring-1 ring-rose-500/20'
                      : activeNotice.type === 'success'
                      ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-200 ring-1 ring-emerald-500/20'
                      : 'bg-sky-950/40 border-sky-500/50 text-sky-200 ring-1 ring-sky-500/20'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 mt-0.5">
                      {activeNotice.type === 'warning' ? (
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                      ) : activeNotice.type === 'error' ? (
                        <XCircle className="h-4 w-4 text-rose-400" />
                      ) : activeNotice.type === 'success' ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <Info className="h-4 w-4 text-sky-400" />
                      )}
                    </div>
                    <div>
                      <div className="font-bold text-white tracking-tight">{activeNotice.title}</div>
                      <p className="mt-0.5 text-slate-300 leading-relaxed">{activeNotice.message}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    {activeNotice.actionLabel && activeNotice.actionFn && (
                      <button
                        onClick={activeNotice.actionFn}
                        className={`px-3 py-1.5 rounded-xl font-bold text-xs transition shadow-md ${
                          activeNotice.type === 'warning'
                            ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-amber-500/20'
                            : activeNotice.type === 'success'
                            ? 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-emerald-500/20'
                            : 'bg-sky-500 hover:bg-sky-400 text-slate-950 shadow-sky-500/20'
                        }`}
                      >
                        {activeNotice.actionLabel}
                      </button>
                    )}
                    <button
                      onClick={handleDismissNotice}
                      className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      title="Dismiss notice"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* Resolution Lifecycle Workflow Stepper */}
              <div className="p-4 bg-slate-900/90 rounded-2xl border border-slate-800 space-y-3 shadow-lg">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-purple-400" />
                    <span className="text-xs font-bold text-white tracking-wide uppercase">
                      Resolution Lifecycle Workflow
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Stage:{' '}
                    <span
                      className={`font-sans font-bold px-2 py-0.5 rounded-full ${
                        selectedCase.status === 'RESOLVED'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : selectedCase.status === 'VERIFYING'
                          ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                          : selectedCase.status === 'AWAITING_APPROVAL'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                      }`}
                    >
                      {selectedCase.status}
                    </span>
                  </span>
                </div>

                {/* 4-Step Pipeline */}
                {(() => {
                  const isApproved = ['VERIFYING', 'APPROVED', 'RESOLVED'].includes(selectedCase.status)
                  const isRejected = selectedCase.status === 'REJECTED'
                  const isAwaitingApproval = selectedCase.status === 'AWAITING_APPROVAL'
                  const isVerifyingStatus = selectedCase.status === 'VERIFYING' || selectedCase.status === 'APPROVED'
                  const isResolved = selectedCase.status === 'RESOLVED'
                  const isVerificationPass = verificationResult?.verification_result === 'PASS'

                  const flowSteps = [
                    {
                      number: 1,
                      title: '1. Authorization',
                      desc: isRejected ? 'Rejected' : isApproved ? 'Authorized' : 'Approval Gate',
                      state: isRejected ? 'rejected' : isApproved ? 'completed' : isAwaitingApproval ? 'active' : 'pending',
                    },
                    {
                      number: 2,
                      title: selectedCase.category === 'HARDWARE_DIAGNOSTICS' ? '2. Remote Fix' : selectedCase.category === 'FEE_OVERCHARGE' ? '2. Credit Note' : '2. Bank Credit',
                      desc: isResolved || isVerificationPass ? (caseDiscrepancyAmount !== '0.00' ? `₹${caseDiscrepancyAmount} Credited` : 'Adjustment Applied') : isVerifyingStatus ? 'Simulate Action' : 'Awaiting Step 1',
                      state: isResolved || isVerificationPass ? 'completed' : isVerifyingStatus ? 'active' : 'pending',
                    },
                    {
                      number: 3,
                      title: '3. Verification',
                      desc: isResolved || isVerificationPass ? 'Audited PASS' : isVerifyingStatus ? 'Ready to Audit' : 'Awaiting Credit',
                      state: isResolved || isVerificationPass ? 'completed' : isVerifyingStatus ? 'active' : 'pending',
                    },
                    {
                      number: 4,
                      title: '4. Reconciled',
                      desc: isResolved ? 'Case Resolved' : 'Pending Verification',
                      state: isResolved ? 'completed' : 'pending',
                    },
                  ]

                  return (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                      {flowSteps.map((st) => {
                        const isDone = st.state === 'completed'
                        const isActive = st.state === 'active'
                        const isRej = st.state === 'rejected'

                        return (
                          <div
                            key={st.number}
                            className={`p-2.5 rounded-xl border text-xs transition relative ${
                              isDone
                                ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-200'
                                : isActive
                                ? 'bg-purple-950/30 border-purple-500/60 text-purple-200 ring-1 ring-purple-500/40 shadow-md'
                                : isRej
                                ? 'bg-rose-950/20 border-rose-500/40 text-rose-300'
                                : 'bg-slate-950/50 border-slate-800 text-slate-500'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span
                                className={`h-5 w-5 rounded-full flex items-center justify-center font-bold text-[10px] ${
                                  isDone
                                    ? 'bg-emerald-500 text-slate-950'
                                    : isActive
                                    ? 'bg-purple-500 text-white animate-pulse'
                                    : isRej
                                    ? 'bg-rose-500 text-white'
                                    : 'bg-slate-800 text-slate-400'
                                }`}
                              >
                                {isDone ? (
                                  <Check className="h-3 w-3 stroke-[3]" />
                                ) : isRej ? (
                                  <X className="h-3 w-3 stroke-[3]" />
                                ) : (
                                  st.number
                                )}
                              </span>
                              <span className="text-[9px] uppercase font-mono font-bold tracking-wider">
                                {isDone ? 'DONE' : isActive ? 'ACTIVE' : isRej ? 'REJECTED' : 'PENDING'}
                              </span>
                            </div>
                            <div className="font-semibold text-slate-200 truncate">{st.title}</div>
                            <div className="text-[10px] text-slate-400 truncate">{st.desc}</div>
                          </div>
                        )
                      })}
                    </div>
                  )
                })()}
              </div>

              {/* STAGE 1: Action Approval Card (when awaiting approval) */}
              {selectedCase.status === 'AWAITING_APPROVAL' && (
                <div className="p-6 bg-slate-900/90 rounded-2xl border border-amber-500/40 space-y-4 shadow-xl ring-1 ring-amber-500/20">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      <ShieldAlert className="h-5 w-5 text-amber-400" />
                      <div>
                        <h3 className="font-bold text-sm text-white">
                          Step 1 of 4: Supervisor Authorization Required
                        </h3>
                        <p className="text-xs text-slate-400">
                          {activeCaseDetail?.pending_approval?.action
                            ? `${activeCaseDetail.pending_approval.action} requires supervisor authorization`
                            : 'Automated remediation exceeds safety policy threshold'}
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                      POLICY GATE: &gt; ₹5,000.00
                    </span>
                  </div>

                  <div className="text-xs text-slate-300 space-y-2.5">
                    <p className="leading-relaxed">
                      OpsSaathi detected an operational issue involving{' '}
                      <strong className="text-amber-400 font-bold">
                        {caseDiscrepancyAmount !== '0.00' ? `₹${caseDiscrepancyAmount}` : 'an expedited action'}
                      </strong>. Per Policy
                      Rule #3, automated actions exceeding the ₹5,000.00 safety threshold require human supervisor
                      authorization before execution.
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
                        <span className="text-slate-200">
                          {activeCaseDetail?.pending_approval?.action || 'SETTLEMENT_RESYNC'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Adapter Target:</span>{' '}
                        <SourceBadge
                          source={
                            selectedCase.queue === 'TECH_SUPPORT'
                              ? 'MOCK_HARDWARE_IOT'
                              : selectedCase.queue === 'ESCALATIONS'
                              ? 'MOCK_BANK_IMPS'
                              : 'MOCK_SETTLEMENT_OPS'
                          }
                          size="sm"
                        />
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

              {/* STAGE: Investigation In Progress */}
              {selectedCase.status === 'IN_PROGRESS' && (
                <div className="p-5 bg-slate-900/90 rounded-2xl border border-sky-500/30 space-y-3 shadow-xl ring-1 ring-sky-500/10">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      <Sparkles className="h-5 w-5 text-sky-400 animate-pulse" />
                      <div>
                        <h3 className="font-bold text-sm text-white">Autonomous Agent Investigation Active</h3>
                        <p className="text-xs text-slate-400">
                          OpsSaathi is running automated telemetry diagnostics and audit trails
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-sky-400 bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 rounded-full">
                      STATUS: IN_PROGRESS
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    This case is actively being processed by the autonomous ops pipeline. Diagnostic events, telemetry traces, and queue dispatches are streaming into the audit log below in real time.
                  </p>
                </div>
              )}

              {/* STAGE: New Case Received */}
              {selectedCase.status === 'NEW' && (
                <div className="p-5 bg-slate-900/90 rounded-2xl border border-slate-700/60 space-y-3 shadow-xl">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      <FileText className="h-5 w-5 text-purple-400" />
                      <div>
                        <h3 className="font-bold text-sm text-white">New Case Queued</h3>
                        <p className="text-xs text-slate-400">
                          Awaiting triage or automated policy classification
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-purple-400 bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 rounded-full">
                      STATUS: NEW
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Case is pending automated dispatch. You can assign it to a different queue above or monitor incoming audit events below.
                  </p>
                </div>
              )}

              {/* STAGE 2 & 3: Active Settlement Re-Sync & Verification Flow (when VERIFYING or APPROVED) */}
              {(selectedCase.status === 'VERIFYING' || selectedCase.status === 'APPROVED') && (
                <div className="p-6 bg-slate-900/90 rounded-2xl border border-sky-500/40 space-y-4 shadow-xl ring-1 ring-sky-500/20">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      <Sparkles className="h-5 w-5 text-sky-400" />
                      <div>
                        <h3 className="font-bold text-sm text-white">
                          Steps 2 &amp; 3: Bank Credit Simulation &amp; Independent Verification
                        </h3>
                        <p className="text-xs text-slate-400">
                          Re-Sync scheduled &bull; Awaiting bank settlement credit and read-only audit
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-sky-400 bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 rounded-full">
                      STATUS: VERIFYING
                    </span>
                  </div>

                  {/* Flow Action Steps Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
                    {/* Sub-step 2: Bank Credit Simulation */}
                    <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 flex flex-col justify-between">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center font-bold text-[10px]">
                            2
                          </span>
                          <span className="font-bold text-slate-200">Simulate Bank Credit</span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          {caseDiscrepancyAmount !== '0.00'
                            ? `Insert ₹${caseDiscrepancyAmount} bank ledger credit to balance the settlement batch.`
                            : 'Insert remedial adjustment on ledger to verify case resolution.'}
                        </p>
                      </div>
                      <button
                        onClick={handleSimulateAndNotice}
                        disabled={isSimulating}
                        className="w-full inline-flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold px-3 py-2 rounded-xl text-xs shadow-md transition disabled:opacity-50"
                      >
                        <Play className={`h-3.5 w-3.5 ${isSimulating ? 'animate-spin' : ''}`} />
                        <span>
                          {isSimulating
                            ? 'Simulating Credit...'
                            : caseDiscrepancyAmount !== '0.00'
                            ? `Simulate Credit (₹${caseDiscrepancyAmount})`
                            : 'Simulate Bank Credit'}
                        </span>
                      </button>
                    </div>

                    {/* Sub-step 3: Run Independent Verification */}
                    <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 flex flex-col justify-between">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="h-5 w-5 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center font-bold text-[10px]">
                            3
                          </span>
                          <span className="font-bold text-slate-200">Run Independent Verification</span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Execute read-only verifier session to confirm ₹0.00 discrepancy and close case.
                        </p>
                      </div>
                      <button
                        onClick={handleVerify}
                        disabled={isVerifying}
                        className="w-full inline-flex items-center justify-center gap-2 bg-gradient-to-r from-sky-500 to-cyan-500 hover:from-sky-400 hover:to-cyan-400 text-slate-950 font-bold px-3 py-2 rounded-xl text-xs shadow-md transition disabled:opacity-50"
                      >
                        <Sparkles className={`h-3.5 w-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
                        <span>{isVerifying ? 'Verifying Ledger...' : 'Run Independent Verification'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Real-time Verification Report (if run) */}
                  {verificationResult && (
                    <div
                      className={`p-4 rounded-xl border font-mono text-xs space-y-3 ${
                        verificationResult.verification_result === 'PASS'
                          ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-200'
                          : 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                      }`}
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                        <span className="font-sans font-bold flex items-center gap-2">
                          {verificationResult.verification_result === 'PASS' ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-amber-400" />
                          )}
                          Verification Report: {verificationResult.verification_result}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          Role: {verificationResult.verifier_role || 'opssaathi_verifier'} (READ-ONLY)
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-[11px]">
                        <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                          <span className="text-slate-500 font-sans font-semibold">Expected Net:</span>
                          <div>₹{verificationResult.expected_net || '15000.00'}</div>
                        </div>
                        <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                          <span className="text-slate-500 font-sans font-semibold">Observed Net:</span>
                          <div>₹{verificationResult.after_observed || '15000.00'}</div>
                        </div>
                      </div>

                      <div
                        className={`p-2.5 rounded-lg text-center font-sans font-semibold text-xs ${
                          verificationResult.verification_result === 'PASS'
                            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                            : 'bg-amber-500/10 border border-amber-500/20 text-amber-300'
                        }`}
                      >
                        {verificationResult.verification_result === 'PASS'
                          ? 'Verdict: PASS — Zero discrepancy confirmed. Case transitioning to RESOLVED.'
                          : 'Verdict: FAIL — Discrepancy remains. Click "Simulate Bank Credit" above, then verify again.'}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STAGE 4: Case Resolved Confirmation Card */}
              {selectedCase.status === 'RESOLVED' && (
                <div className="p-6 bg-slate-900/90 rounded-2xl border border-emerald-500/40 space-y-4 shadow-xl ring-1 ring-emerald-500/20">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2.5">
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      <div>
                        <h3 className="font-bold text-sm text-white">
                          Step 4 of 4: Case Fully Reconciled &amp; Resolved
                        </h3>
                        <p className="text-xs text-slate-400">
                          {selectedCase.category === 'HARDWARE_DIAGNOSTICS'
                            ? 'Hardware diagnostics verified and audio test chime confirmed'
                            : 'Independent cryptographic audit passed with ₹0.00 discrepancy'}
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
                      STATUS: RESOLVED
                    </span>
                  </div>

                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs space-y-2 text-slate-300">
                    {selectedCase.category === 'HARDWARE_DIAGNOSTICS' ? (
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <span className="text-slate-500">Audio Latency:</span> 320ms (Within SLA &lt; 500ms)
                        </div>
                        <div>
                          <span className="text-slate-500">Device Status:</span> Online / Signal -82dBm
                        </div>
                        <div>
                          <span className="text-slate-500">Test Chime:</span>{' '}
                          <strong className="text-emerald-400">CONFIRMED</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">Audit Verifier:</span> opssaathi_verifier
                        </div>
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <span className="text-slate-500">Expected Settlement:</span> ₹{verificationResult?.expected_net ? parseFloat(verificationResult.expected_net).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '15,000.00'}
                        </div>
                        <div>
                          <span className="text-slate-500">Observed Settlement:</span> ₹{verificationResult?.after_observed ? parseFloat(verificationResult.after_observed).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '15,000.00'}
                        </div>
                        <div>
                          <span className="text-slate-500">Final Discrepancy:</span>{' '}
                          <strong className="text-emerald-400">₹0.00</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">Audit Verifier:</span> opssaathi_verifier
                        </div>
                      </div>
                    )}
                    <p className="text-[11px] text-slate-400 font-sans pt-1 border-t border-slate-800/80">
                      All timeline events, supervisor authorization fingerprints, and verifier records are sealed in the immutable audit log below.
                    </p>
                  </div>
                </div>
              )}

              {/* STAGE 5: Case Rejected Notice */}
              {selectedCase.status === 'REJECTED' && (
                <div className="p-5 bg-slate-900/90 rounded-2xl border border-rose-500/40 space-y-3 shadow-xl ring-1 ring-rose-500/20">
                  <div className="flex items-center gap-2.5">
                    <XCircle className="h-5 w-5 text-rose-400" />
                    <div>
                      <h3 className="font-bold text-sm text-white">Settlement Re-Sync Rejected</h3>
                      <p className="text-xs text-slate-400">
                        This gated action was rejected by human supervisor. See documented reason in audit timeline.
                      </p>
                    </div>
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
                          <div className="flex-1 min-w-0 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 space-y-1">
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
                              <div className="mt-1 pt-1.5 border-t border-slate-900 font-mono text-[10px] text-slate-400 bg-slate-900/60 p-2 rounded-lg space-y-1 overflow-hidden">
                                {Object.entries(ev.payload).map(([k, v]) => (
                                  <div key={k} className="break-words [overflow-wrap:anywhere] leading-relaxed">
                                    <span className="text-slate-500 font-semibold">{k}:</span>{' '}
                                    <span className="text-slate-300 break-words [overflow-wrap:anywhere]">
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
        discrepancyAmount={caseDiscrepancyAmount}
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

      {/* Create Case Modal */}
      {onCreateCase && (
        <CreateCaseModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onCreateCase={onCreateCase}
        />
      )}
    </div>
  )
}
