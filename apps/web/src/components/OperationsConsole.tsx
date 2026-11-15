import { useState, useMemo, FC } from 'react'
import {
  SupportCaseItem,
  CaseDetail,
  VerificationResult,
  OutcomeMetrics,
} from '../types/api'
import { SourceBadge } from './SourceBadge'
import { StatusChip, CaseStatus } from './StatusChip'
import { ApprovalModal } from './ApprovalModal'
import { RejectModal } from './RejectModal'
import { CreateCaseModal } from './CreateCaseModal'
import { MetricsTile } from './MetricsTile'
import { Button } from './Button'
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Play,
  Sparkles,
  PlusCircle,
  Search,
  Clock,
  History,
  AlertTriangle,
  X,
  FileCheck,
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
        message: `₹${caseDiscrepancyAmount} credit recorded on ledger. Proceed to Step 3: click "Run Independent Verification" to close case.`,
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
        message: 'Case is now in VERIFYING status. Step 2: Click "Simulate Credit" to deposit credit, then verify.',
        actionLabel: caseDiscrepancyAmount !== '0.00' ? `Simulate Credit (₹${caseDiscrepancyAmount})` : 'Simulate Bank Credit',
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
        message: `Settlement re-sync rejected: "${reason}". Documented in audit log.`,
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
        message: `Case ${selectedCase.case_number} reassigned to ${targetAssignQueue}.`,
      })
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Reassignment Failed',
        message: err?.message || 'Could not reassign case queue.',
      })
    } finally {
      setIsAssigning(false)
    }
  }

  const handleVerify = async () => {
    if (!selectedCase) return
    try {
      setIsVerifying(true)
      await onVerifyCase(selectedCase.id)
    } catch (err: any) {
      setLocalNotice({
        type: 'error',
        title: 'Verification Failed',
        message: err?.message || 'Independent verification failed.',
      })
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="w-full space-y-6 font-sans text-ink-primary">
      {/* Metrics Banner */}
      <MetricsTile
        metrics={metrics || null}
        onRefresh={onRefreshMetrics}
        isLoading={isLoadingMetrics}
      />

      {/* Top Search, Queue Filter & Action Controls */}
      <div className="bg-surface-card rounded-card border border-surface-border p-4 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-ink-muted absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by case #, order reference, or summary..."
              className="w-full min-h-12 pl-10 pr-4 bg-surface-subtle border border-surface-border rounded-xl text-xs sm:text-sm text-ink-primary placeholder:text-ink-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan transition"
            />
          </div>

          {/* New Case Button */}
          {onCreateCase && (
            <Button
              variant="primary"
              onClick={() => setIsCreateModalOpen(true)}
              className="gap-2 text-xs min-h-12 px-4 whitespace-nowrap"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Create Case</span>
            </Button>
          )}
        </div>

        {/* Queue and Status Filter Chips */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-surface-divider">
          {/* Queue Pills */}
          <div className="flex flex-wrap gap-1.5">
            {QUEUES.map((q) => {
              const isSelected = selectedQueue === q.id
              const count = queueCounts[q.id] || 0
              return (
                <button
                  key={q.id}
                  type="button"
                  onClick={() => setSelectedQueue(q.id)}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition ${
                    isSelected
                      ? 'bg-paytm-navy text-white shadow-xs'
                      : 'bg-surface-subtle text-ink-secondary hover:text-ink-primary hover:bg-surface-border'
                  }`}
                >
                  {q.label}
                  <span
                    className={`ml-1.5 px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${
                      isSelected ? 'bg-paytm-cyan text-paytm-navy' : 'bg-surface-card text-ink-muted'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Status Dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-ink-secondary">
            <span>Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-surface-subtle border border-surface-border rounded-lg px-2.5 py-1.5 text-xs text-ink-primary outline-none cursor-pointer focus-visible:ring-2 focus-visible:ring-paytm-cyan"
            >
              {STATUSES.map((st) => (
                <option key={st} value={st}>
                  {st === 'ALL' ? 'All Statuses' : st.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Notice Banner */}
      {activeNotice && (
        <div
          role="alert"
          className={`p-4 rounded-card border shadow-xs flex items-start justify-between gap-3 ${
            activeNotice.type === 'success'
              ? 'bg-status-completed-bg border-status-completed-border text-status-completed-text'
              : activeNotice.type === 'error'
              ? 'bg-status-rejected-bg border-status-rejected-border text-status-rejected-text'
              : 'bg-status-approval-bg border-status-approval-border text-status-approval-text'
          }`}
        >
          <div className="flex items-start gap-3">
            {activeNotice.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-status-completed-text" />
            ) : activeNotice.type === 'error' ? (
              <XCircle className="w-5 h-5 shrink-0 mt-0.5 text-status-rejected-text" />
            ) : (
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-status-approval-text" />
            )}
            <div>
              <h4 className="text-sm font-semibold">{activeNotice.title}</h4>
              <p className="text-xs mt-0.5 opacity-90">{activeNotice.message}</p>
              {activeNotice.actionLabel && activeNotice.actionFn && (
                <Button
                  variant="primary"
                  onClick={activeNotice.actionFn}
                  className="mt-2 text-xs min-h-10 px-3 bg-paytm-navy text-white hover:bg-paytm-navy-hover"
                >
                  {activeNotice.actionLabel}
                </Button>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={handleDismissNotice}
            className="p-1 rounded-lg text-ink-muted hover:text-ink-primary"
            aria-label="Dismiss notice"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Split Main View (Left: Queue Cases 5 cols, Right: Selected Case Detail 7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Case Queue List (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between pb-1 px-1">
            <h3 className="text-sm font-semibold text-paytm-navy">
              Dispute Queue ({filteredCases.length})
            </h3>
            <span className="text-[11px] text-ink-muted font-mono">
              Filter: {selectedQueue}
            </span>
          </div>

          <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {filteredCases.length === 0 ? (
              <div className="p-8 text-center bg-surface-card rounded-card border border-surface-border text-ink-muted text-xs">
                No cases match the selected filters.
              </div>
            ) : (
              filteredCases.map((c) => {
                const isSelected = selectedCase?.id === c.id
                const isAwaitingApproval = c.status === 'AWAITING_APPROVAL'

                return (
                  <div
                    key={c.id}
                    onClick={() => onSelectCase(c.id)}
                    tabIndex={0}
                    role="button"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSelectCase(c.id)
                      }
                    }}
                    className={`p-4 rounded-card border transition cursor-pointer text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${
                      isSelected
                        ? 'bg-paytm-cyan-light/70 border-paytm-cyan/60 shadow-xs'
                        : 'bg-surface-card border-surface-border hover:bg-surface-subtle shadow-xs'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-paytm-navy text-xs">
                          {c.case_number}
                        </span>
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-surface-subtle text-ink-secondary border border-surface-border">
                          {c.priority}
                        </span>
                      </div>
                      <StatusChip status={c.status as CaseStatus} />
                    </div>

                    <p className="mt-2 text-ink-primary font-medium line-clamp-2 leading-relaxed">
                      {c.summary}
                    </p>

                    <div className="mt-2.5 pt-2 border-t border-surface-divider flex items-center justify-between text-[11px] text-ink-secondary">
                      <span>Queue: <strong className="text-ink-primary">{c.queue}</strong></span>
                      <span className="flex items-center gap-1 font-mono text-[10px] text-ink-muted">
                        <Clock className="w-3 h-3 text-ink-muted" />
                        {new Date(c.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    {isAwaitingApproval && (
                      <div className="mt-2 p-1.5 rounded-lg bg-status-approval-bg border border-status-approval-border text-[11px] font-semibold text-status-approval-text flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-status-approval-text shrink-0" />
                        <span>Action Sign-Off Required (&gt; ₹5,000 threshold)</span>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Right Column: Split Case Detail View (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {selectedCase ? (
            <div className="space-y-4">
              {/* Case Header Card */}
              <div className="bg-surface-card rounded-card border border-surface-border p-5 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-divider">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-paytm-navy font-mono">
                        {selectedCase.case_number}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-surface-subtle text-paytm-navy border border-surface-border">
                        v{selectedCase.version}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-status-rejected-bg text-status-rejected-text border border-status-rejected-border">
                        {selectedCase.priority}
                      </span>
                    </div>
                    <p className="text-xs text-ink-secondary mt-1 font-medium">{selectedCase.summary}</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusChip status={selectedCase.status as CaseStatus} />
                    <button
                      type="button"
                      onClick={() => onSelectCase('')}
                      className="p-1 rounded-lg text-ink-muted hover:text-ink-primary hover:bg-surface-subtle"
                      title="Close case detail"
                      aria-label="Close case detail"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Queue Re-assignment and Actions Bar */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-ink-secondary font-medium">Reassign Queue:</span>
                    <select
                      value={targetAssignQueue}
                      onChange={(e) => setTargetAssignQueue(e.target.value)}
                      className="bg-surface-subtle border border-surface-border rounded-lg px-2.5 py-1.5 text-xs text-ink-primary outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan cursor-pointer"
                    >
                      <option value="SETTLEMENT_OPS">Settlement Ops</option>
                      <option value="SETTLEMENTS">Settlements</option>
                      <option value="TECH_SUPPORT">Tech Support</option>
                      <option value="ESCALATIONS">Escalations</option>
                    </select>
                    <Button
                      variant="secondary"
                      onClick={handleAssign}
                      disabled={isAssigning}
                      className="text-xs min-h-10 px-3"
                    >
                      {isAssigning ? 'Updating...' : 'Assign'}
                    </Button>
                  </div>

                  <SourceBadge source="MOCK_SETTLEMENT_OPS" size="sm" />
                </div>
              </div>

              {/* ACTION STAGES */}

              {/* STAGE 1: Action Approval Card (when AWAITING_APPROVAL) */}
              {selectedCase.status === 'AWAITING_APPROVAL' && (
                <div className="bg-surface-card rounded-card border border-status-approval-border p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-surface-divider">
                    <div className="flex items-center gap-2.5">
                      <ShieldAlert className="w-5 h-5 text-status-approval-text" />
                      <div>
                        <h4 className="font-bold text-sm text-paytm-navy">
                          Step 1 of 4: Supervisor Authorization Required
                        </h4>
                        <p className="text-xs text-ink-secondary">
                          Two-key discipline safety policy gate triggered
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-status-approval-text bg-status-approval-bg border border-status-approval-border px-2 py-0.5 rounded-full">
                      POLICY GATE: &gt; ₹5,000.00
                    </span>
                  </div>

                  <p className="text-xs text-ink-secondary leading-relaxed">
                    OpsSaathi identified an overdue settlement deficit of{' '}
                    <strong className="text-status-approval-text font-bold">
                      ₹{caseDiscrepancyAmount}
                    </strong>. Automated remediation requires explicit supervisor authorization before ledger write.
                  </p>

                  <div className="flex items-center gap-3 pt-2">
                    <Button
                      variant="primary"
                      onClick={() => setIsApprovalModalOpen(true)}
                      className="flex-1 min-h-12 text-xs font-semibold gap-2"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Review &amp; Authorize Action</span>
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setIsRejectModalOpen(true)}
                      className="min-h-12 text-xs font-semibold text-status-rejected-text border-status-rejected-border hover:bg-status-rejected-bg gap-2"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Reject</span>
                    </Button>
                  </div>
                </div>
              )}

              {/* STAGES 2 & 3: Bank Credit Simulation & Independent Verification (when VERIFYING or APPROVED) */}
              {(selectedCase.status === 'VERIFYING' || selectedCase.status === 'APPROVED') && (
                <div className="bg-surface-card rounded-card border border-paytm-cyan/40 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-surface-divider">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-paytm-navy" />
                      <h4 className="font-bold text-sm text-paytm-navy">
                        Steps 2 &amp; 3: Bank Credit Simulation &amp; Independent Verification
                      </h4>
                    </div>
                    <StatusChip status="VERIFYING" />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {/* Step 2 Card */}
                    <div className="p-4 bg-surface-subtle rounded-xl border border-surface-border flex flex-col justify-between space-y-3">
                      <div>
                        <div className="flex items-center gap-2 font-bold text-ink-primary">
                          <span className="w-5 h-5 rounded-full bg-paytm-navy text-white flex items-center justify-center text-[10px]">
                            2
                          </span>
                          <span>Simulate Bank Credit</span>
                        </div>
                        <p className="text-[11px] text-ink-secondary mt-1">
                          Deposit ₹{caseDiscrepancyAmount} credit to balance the ledger batch.
                        </p>
                      </div>
                      <Button
                        variant="secondary"
                        onClick={handleSimulateAndNotice}
                        disabled={isSimulating}
                        className="w-full min-h-12 text-xs font-semibold gap-1.5"
                      >
                        <Play className={`w-3.5 h-3.5 ${isSimulating ? 'animate-spin' : ''}`} />
                        <span>{isSimulating ? 'Simulating Credit...' : `Simulate Credit (₹${caseDiscrepancyAmount})`}</span>
                      </Button>
                    </div>

                    {/* Step 3 Card */}
                    <div className="p-4 bg-surface-subtle rounded-xl border border-surface-border flex flex-col justify-between space-y-3">
                      <div>
                        <div className="flex items-center gap-2 font-bold text-ink-primary">
                          <span className="w-5 h-5 rounded-full bg-paytm-cyan text-paytm-navy flex items-center justify-center text-[10px]">
                            3
                          </span>
                          <span>Run Independent Verification</span>
                        </div>
                        <p className="text-[11px] text-ink-secondary mt-1">
                          Execute read-only verification session to confirm ₹0.00 discrepancy.
                        </p>
                      </div>
                      <Button
                        variant="primary"
                        onClick={handleVerify}
                        disabled={isVerifying}
                        className="w-full min-h-12 text-xs font-semibold gap-1.5"
                      >
                        <Sparkles className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
                        <span>{isVerifying ? 'Verifying Ledger...' : 'Run Independent Verification'}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Real-time Verification Report Card */}
                  {verificationResult && (
                    <div
                      className={`p-4 rounded-xl border font-mono text-xs space-y-3 ${
                        verificationResult.verification_result === 'PASS'
                          ? 'bg-status-completed-bg border-status-completed-border text-status-completed-text'
                          : 'bg-status-approval-bg border-status-approval-border text-status-approval-text'
                      }`}
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
                        <span className="font-sans font-bold flex items-center gap-2">
                          {verificationResult.verification_result === 'PASS' ? (
                            <CheckCircle2 className="w-4 h-4 text-status-completed-text" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-status-approval-text" />
                          )}
                          Verification Result: {verificationResult.verification_result}
                        </span>
                        <span className="text-[10px] text-ink-secondary font-mono">
                          Verifier: {verificationResult.verifier_role || 'opssaathi_verifier'} (READ-ONLY)
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-[11px]">
                        <div className="p-2.5 bg-surface-card rounded-lg border border-surface-border text-ink-primary">
                          <span className="text-ink-secondary font-sans font-medium block">Expected Net:</span>
                          <span className="font-bold text-sm">₹{verificationResult.expected_net || '15000.00'}</span>
                        </div>
                        <div className="p-2.5 bg-surface-card rounded-lg border border-surface-border text-ink-primary">
                          <span className="text-ink-secondary font-sans font-medium block">Observed Net:</span>
                          <span className="font-bold text-sm">₹{verificationResult.after_observed || '15000.00'}</span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded-lg text-center font-sans font-semibold text-xs bg-surface-card border border-surface-border text-ink-primary">
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
                <div className="bg-surface-card rounded-card border border-status-completed-border p-5 shadow-sm space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
                    <div className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-5 h-5 text-status-completed-text" />
                      <div>
                        <h4 className="font-bold text-sm text-status-completed-text">
                          Case Fully Reconciled &amp; Resolved
                        </h4>
                        <p className="text-xs text-ink-secondary">
                          Independent cryptographic verification confirmed ₹0.00 discrepancy
                        </p>
                      </div>
                    </div>
                    <StatusChip status="RESOLVED" />
                  </div>

                  <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border text-xs text-ink-secondary space-y-1">
                    <div className="flex justify-between">
                      <span>Audit Verifier:</span>
                      <strong className="font-mono text-ink-primary">opssaathi_verifier (READ-ONLY)</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Ledger Balance:</span>
                      <strong className="text-status-completed-text">₹0.00 Discrepancy (100% Balanced)</strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Case Timeline / Audit Trail */}
              <div className="bg-surface-card rounded-card border border-surface-border p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-paytm-navy" />
                    <h4 className="font-bold text-sm text-paytm-navy">
                      Audit Trail &amp; Case Timeline ({activeCaseDetail?.timeline?.length || 0} events)
                    </h4>
                  </div>
                  <FileCheck className="w-4 h-4 text-ink-muted" />
                </div>

                {isLoadingDetail ? (
                  <div className="p-6 text-center text-xs text-ink-muted">Loading timeline...</div>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {(activeCaseDetail?.timeline || []).map((evt, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-surface-subtle rounded-xl border border-surface-border text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-paytm-navy">{evt.event_type}</span>
                          <span className="font-mono text-[10px] text-ink-muted">
                            {new Date(evt.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-ink-secondary text-[11px]">
                          {evt.payload?.summary ||
                            evt.payload?.reason ||
                            (evt.payload?.description as string) ||
                            `${evt.actor}: ${evt.from_status || 'NEW'} → ${evt.to_status || 'IN_PROGRESS'}`}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-surface-card rounded-card border border-surface-border shadow-sm text-ink-muted space-y-2">
              <History className="w-8 h-8 mx-auto text-ink-muted" />
              <h4 className="text-sm font-semibold text-ink-primary">No Case Selected</h4>
              <p className="text-xs text-ink-secondary max-w-sm mx-auto">
                Select a dispute case from the queue on the left to inspect its investigation evidence, authorize policy actions, and verify resolutions.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {isApprovalModalOpen && selectedCase && (
        <ApprovalModal
          isOpen={isApprovalModalOpen}
          onClose={() => setIsApprovalModalOpen(false)}
          caseItem={selectedCase}
          pendingApproval={activeCaseDetail?.pending_approval || null}
          discrepancyAmount={caseDiscrepancyAmount}
          onConfirmApprove={handleApproveConfirm}
          isApproving={isApproving}
        />
      )}

      {isRejectModalOpen && selectedCase && (
        <RejectModal
          isOpen={isRejectModalOpen}
          onClose={() => setIsRejectModalOpen(false)}
          caseItem={selectedCase}
          pendingApproval={activeCaseDetail?.pending_approval || null}
          onConfirmReject={handleRejectConfirm}
          isRejecting={isRejecting}
        />
      )}

      {isCreateModalOpen && onCreateCase && (
        <CreateCaseModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onCreateCase={onCreateCase}
        />
      )}
    </div>
  )
}
