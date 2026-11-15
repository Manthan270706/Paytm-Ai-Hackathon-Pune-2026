import { useState, FC } from 'react'
import {
  MerchantProfile,
  TransactionItem,
  SettlementBatchItem,
  SupportCaseItem,
} from '../types/api'
import { SourceBadge } from './SourceBadge'
import { StatusChip, CaseStatus } from './StatusChip'
import { Stepper, StepItem } from './Stepper'
import { BottomNav, MerchantTab } from './BottomNav'
import { ListRow } from './ListRow'
import { Card } from './Card'
import { Button } from './Button'
import { EmptyState } from './EmptyState'
import { MerchantCaseModal } from './MerchantCaseModal'
import {
  MessageSquare,
  AlertTriangle,
  Receipt,
  Phone,
  Sparkles,
  ShieldCheck,
} from 'lucide-react'
import { WatchdogAlert } from '../types/api'
import { WatchdogBanner } from './WatchdogBanner'

interface MerchantDashboardProps {
  profile: MerchantProfile | null
  transactions: TransactionItem[]
  settlements: SettlementBatchItem[]
  cases: SupportCaseItem[]
  discrepancy: string
  loading: boolean
  error: string | null
  token?: string
  currentLanguage?: string
  watchdogAlert?: WatchdogAlert | null
  onRunWatchdogScan?: () => Promise<void>
  onOpenChargeback?: (caseId: string) => void
  onOpenChat: (presetPrompt?: string) => void
}

export const MerchantDashboard: FC<MerchantDashboardProps> = ({
  profile,
  transactions,
  settlements,
  cases,
  discrepancy,
  loading,
  error,
  token = 'demo-token-merchant-1',
  currentLanguage = 'en',
  watchdogAlert = null,
  onRunWatchdogScan,
  onOpenChargeback,
  onOpenChat,
}) => {
  const [activeTab, setActiveTab] = useState<MerchantTab>('home')
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse font-sans">
        <div className="h-24 bg-surface-subtle rounded-card border border-surface-border" />
        <div className="h-44 bg-surface-subtle rounded-card border border-surface-border" />
        <div className="h-32 bg-surface-subtle rounded-card border border-surface-border" />
      </div>
    )
  }

  if (error) {
    return (
      <div
        role="alert"
        className="p-4 bg-status-rejected-bg border border-status-rejected-border rounded-xl text-status-rejected-text flex items-center gap-3 font-sans"
      >
        <AlertTriangle className="h-5 w-5 shrink-0" />
        <div>
          <h3 className="font-semibold text-sm">Unable to load merchant overview</h3>
          <p className="text-xs text-ink-secondary mt-0.5">{error}</p>
        </div>
      </div>
    )
  }

  const discrepancyVal = parseFloat(discrepancy || '0')
  const isReconciled = discrepancyVal === 0

  const expectedTotal =
    transactions.length > 0
      ? transactions
          .filter((t) => t.status === 'SUCCESS')
          .reduce((sum, t) => sum + parseFloat(t.amount || '0'), 0)
      : 15000.0

  const observedTotal =
    settlements.length > 0
      ? settlements.reduce((sum, b) => sum + parseFloat(b.net || '0'), 0)
      : 9000.0

  // Dynamic live today string and times
  const todayDateStr = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  const shortDateStr = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
  })

  // Stepper state derived from most recent active case
  const activeCase = cases.length > 0 ? cases[0] : null
  const getStepperSteps = (caseItem: SupportCaseItem | null): StepItem[] => {
    const status = caseItem?.status || 'IN_PROGRESS'
    const now = new Date()
    const tReported = new Date(now.getTime() - 48 * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const tChecking = new Date(now.getTime() - 44 * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    return [
      {
        id: 'reported',
        label: 'Reported',
        description: 'Issue logged',
        state: 'completed',
        timestamp: `${shortDateStr}, ${tReported}`,
      },
      {
        id: 'checking',
        label: 'Checking',
        description: 'Ledger verified',
        state: status === 'NEW' ? 'current' : 'completed',
        timestamp: `${shortDateStr}, ${tChecking}`,
      },
      {
        id: 'support',
        label: 'With Support',
        description: 'Supervisor approval',
        state:
          status === 'AWAITING_APPROVAL'
            ? 'current'
            : status === 'APPROVED' || status === 'VERIFYING' || status === 'RESOLVED'
            ? 'completed'
            : 'upcoming',
        timestamp: status === 'AWAITING_APPROVAL' ? 'Pending Action' : undefined,
      },
      {
        id: 'verified',
        label: 'Verified',
        description: 'Bank credit match',
        state:
          status === 'VERIFYING'
            ? 'current'
            : status === 'RESOLVED'
            ? 'completed'
            : 'upcoming',
      },
      {
        id: 'resolved',
        label: 'Resolved',
        description: 'Ledger closed',
        state: status === 'RESOLVED' ? 'completed' : 'upcoming',
      },
    ]
  }

  const categoryChips = [
    { label: 'Settlement delay', prompt: "Why is ₹6,000.00 missing from today's settlement?" },
    { label: 'Refund issue', prompt: 'I want to check the status of customer refund for order #1082' },
    { label: 'Charges & Fees', prompt: 'What are the charges applied to my daily settlement batch?' },
    { label: 'Soundbox device', prompt: 'My Paytm Soundbox did not announce payment received' },
    { label: 'Other question', prompt: 'I need assistance reviewing an operational issue with my account' },
  ]

  const triggerChat = (prompt: string) => {
    setActiveTab('help')
    onOpenChat(prompt)
    setTimeout(() => {
      const chatElem = document.querySelector('input[placeholder*="Ask OpsSaathi"]') as HTMLInputElement
      if (chatElem) {
        chatElem.scrollIntoView({ behavior: 'smooth' })
        chatElem.focus()
      }
    }, 150)
  }

  return (
    <div className="w-full max-w-md mx-auto sm:max-w-3xl pb-20 font-sans space-y-6 text-ink-primary">
      {/* Merchant Header Card */}
      <div className="bg-surface-card rounded-card border border-surface-border p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-paytm-navy text-white flex items-center justify-center font-bold text-lg shadow-xs">
            {profile?.display_name ? profile.display_name.charAt(0) : 'S'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-paytm-navy tracking-tight">
                {profile?.display_name || 'Sharma General Store'}
              </h2>
              <SourceBadge source={profile?.source_type || 'SYNTHETIC_DEMO'} size="sm" />
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-secondary mt-0.5">
              <span className="flex items-center gap-1 font-mono">
                <Phone className="w-3 h-3 text-ink-muted" />
                {profile?.masked_phone || '+91 98****1234'}
              </span>
              <span>•</span>
              <span className="font-mono text-[11px] text-ink-muted">
                MID: {profile?.id ? profile.id.slice(0, 8) : '11111111'}
              </span>
            </div>
          </div>
        </div>

        <Button
          variant="secondary"
          onClick={() => triggerChat('Check my daily settlement balance')}
          className="gap-2 text-xs min-h-10 px-3 self-start sm:self-center"
        >
          <Sparkles className="w-3.5 h-3.5 text-paytm-navy" />
          <span>Quick Help</span>
        </Button>
      </div>

      {/* Navigation Pills (Mobile top view & Desktop switcher) */}
      <div className="flex items-center gap-1.5 p-1 bg-surface-subtle rounded-xl border border-surface-border overflow-x-auto text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveTab('home')}
          className={`flex-1 min-h-10 px-3 py-1.5 rounded-lg transition text-center ${
            activeTab === 'home'
              ? 'bg-surface-card text-paytm-navy font-semibold shadow-xs'
              : 'text-ink-secondary hover:text-ink-primary'
          }`}
        >
          Overview
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('payments')}
          className={`flex-1 min-h-10 px-3 py-1.5 rounded-lg transition text-center ${
            activeTab === 'payments'
              ? 'bg-surface-card text-paytm-navy font-semibold shadow-xs'
              : 'text-ink-secondary hover:text-ink-primary'
          }`}
        >
          Payments ({transactions.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('settlements')}
          className={`flex-1 min-h-10 px-3 py-1.5 rounded-lg transition text-center ${
            activeTab === 'settlements'
              ? 'bg-surface-card text-paytm-navy font-semibold shadow-xs'
              : 'text-ink-secondary hover:text-ink-primary'
          }`}
        >
          Settlements
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('help')}
          className={`flex-1 min-h-10 px-3 py-1.5 rounded-lg transition text-center flex items-center justify-center gap-1 ${
            activeTab === 'help'
              ? 'bg-surface-card text-paytm-navy font-semibold shadow-xs'
              : 'text-ink-secondary hover:text-ink-primary'
          }`}
        >
          <span>Ask OpsSaathi</span>
          {cases.length > 0 && (
            <span className="w-2 h-2 rounded-full bg-paytm-cyan" />
          )}
        </button>
      </div>

      {/* TAB 1: OVERVIEW (HOME) */}
      {activeTab === 'home' && (
        <div className="space-y-6">
          {/* Proactive Settlement Watchdog Banner */}
          {watchdogAlert && (
            <WatchdogBanner
              alert={watchdogAlert}
              currentLanguage={currentLanguage}
              onScanNow={onRunWatchdogScan}
              onViewCase={(cId) => setSelectedCaseId(cId)}
            />
          )}

          {/* Primary 3-Number Settlement Summary Card */}
          <div className="bg-surface-card rounded-card border border-surface-border p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-surface-divider">
              <div>
                <h3 className="text-sm font-semibold text-paytm-navy">
                  Settlement Summary ({todayDateStr})
                </h3>
                <p className="text-xs text-ink-secondary mt-0.5">
                  Daily settlement balance calculation
                </p>
              </div>
              <SourceBadge source="SYNTHETIC_DEMO" size="sm" />
            </div>

            {/* 3 Prominent Numbers */}
            <div className="grid grid-cols-3 gap-2 sm:gap-4 text-center">
              {/* Number 1: Expected */}
              <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border">
                <span className="text-[11px] font-medium text-ink-secondary block">
                  Expected
                </span>
                <span className="text-base sm:text-xl font-bold text-ink-primary tracking-tight mt-1 block">
                  ₹{expectedTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-ink-muted hidden sm:block mt-0.5">
                  Verified captures
                </span>
              </div>

              {/* Number 2: Received in Bank */}
              <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border">
                <span className="text-[11px] font-medium text-ink-secondary block">
                  Received
                </span>
                <span className="text-base sm:text-xl font-bold text-ink-primary tracking-tight mt-1 block">
                  ₹{observedTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-ink-muted hidden sm:block mt-0.5">
                  Credited to bank
                </span>
              </div>

              {/* Number 3: Difference / Discrepancy */}
              <div
                className={`p-3 rounded-xl border ${
                  isReconciled
                    ? 'bg-status-completed-bg border-status-completed-border'
                    : 'bg-status-approval-bg border-status-approval-border'
                }`}
              >
                <span
                  className={`text-[11px] font-semibold block ${
                    isReconciled ? 'text-status-completed-text' : 'text-status-approval-text'
                  }`}
                >
                  {isReconciled ? 'Status' : 'Pending'}
                </span>
                <span
                  className={`text-base sm:text-xl font-black tracking-tight mt-1 block ${
                    isReconciled ? 'text-status-completed-text' : 'text-status-approval-text'
                  }`}
                >
                  {isReconciled
                    ? '₹0.00'
                    : `₹${discrepancyVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                </span>
                <span
                  className={`text-[10px] hidden sm:block mt-0.5 ${
                    isReconciled ? 'text-status-completed-text' : 'text-status-approval-text'
                  }`}
                >
                  {isReconciled ? 'Fully balanced' : 'Re-sync pending'}
                </span>
              </div>
            </div>

            {/* Big Primary Action: Ask OpsSaathi */}
            <Button
              variant="primary"
              onClick={() => triggerChat("Why is ₹6,000.00 missing from today's settlement?")}
              className="w-full min-h-12 text-sm font-semibold shadow-xs gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Ask OpsSaathi: Check My Settlement</span>
            </Button>
          </div>

          {/* Open Dispute Tracking Banner with Stepper */}
          {activeCase && (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-paytm-navy">
                    Active Support Ticket
                  </h3>
                  <span className="font-mono text-xs text-ink-secondary">
                    #{activeCase.case_number}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {onOpenChargeback && (
                    <Button
                      variant="secondary"
                      onClick={() => onOpenChargeback(activeCase.id)}
                      className="text-xs min-h-10 px-2.5 border-paytm-cyan text-paytm-navy font-semibold hover:bg-paytm-cyan/10 flex items-center gap-1"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-paytm-navy" />
                      <span>Dispute Defense</span>
                    </Button>
                  )}
                  <StatusChip status={(activeCase.status as CaseStatus) || 'IN_PROGRESS'} />
                </div>
              </div>

              <Stepper
                steps={getStepperSteps(activeCase)}
                nextUpdateText="Next update by 4:00 PM IST"
              />
            </div>
          )}

          {/* Recent Payments Peek */}
          <div className="bg-surface-card rounded-card border border-surface-border p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
              <div className="flex items-center gap-2">
                <Receipt className="w-4 h-4 text-paytm-navy" />
                <h4 className="text-sm font-semibold text-ink-primary">
                  Recent Customer Payments
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('payments')}
                className="text-xs font-semibold text-paytm-navy hover:underline"
              >
                View all ({transactions.length})
              </button>
            </div>

            <div className="space-y-1 divide-y divide-surface-divider">
              {transactions.slice(0, 3).map((txn) => {
                const txnDate = txn.txn_time ? new Date(txn.txn_time) : new Date()
                const formattedTime = txnDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                return (
                  <ListRow
                    key={txn.id}
                    title={txn.provider_txn_id}
                    subtitle={`${txn.order_id} • ${formattedTime}`}
                    amount={`₹${parseFloat(txn.amount || '0').toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
                    onActivate={() => triggerChat(`Tell me about payment ${txn.provider_txn_id}`)}
                  />
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: PAYMENTS */}
      {activeTab === 'payments' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
            <div>
              <h3 className="text-sm font-semibold text-paytm-navy">
                Payment Transactions
              </h3>
              <p className="text-xs text-ink-secondary">
                Customer UPI, Card & Wallet captures
              </p>
            </div>
            <span className="text-xs font-semibold text-ink-secondary">
              Total: ₹{expectedTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>

          {transactions.length === 0 ? (
            <EmptyState
              title="No transactions yet"
              description="Captured transactions will appear here once customers pay."
            />
          ) : (
            <div className="bg-surface-card rounded-card border border-surface-border divide-y divide-surface-divider overflow-hidden shadow-sm">
              {transactions.map((txn) => {
                const txnDate = txn.txn_time ? new Date(txn.txn_time) : new Date()
                const formattedTime = txnDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                const formattedDate = txnDate.toLocaleDateString([], { day: 'numeric', month: 'short' })
                return (
                  <div key={txn.id} className="p-3.5 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-ink-primary truncate">
                          {txn.provider_txn_id}
                        </span>
                        <SourceBadge source={txn.source_type} size="sm" />
                      </div>
                      <p className="text-[11px] text-ink-secondary mt-0.5 flex items-center gap-1.5 truncate">
                        <span>Order: {txn.order_id}</span>
                        <span>•</span>
                        <span className="font-mono text-[10px] text-ink-muted">
                          {formattedDate}, {formattedTime}
                        </span>
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-bold text-ink-primary block">
                        ₹{parseFloat(txn.amount || '0').toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                      <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold bg-status-completed-bg text-status-completed-text border border-status-completed-border mt-0.5">
                        {txn.status}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: SETTLEMENTS */}
      {activeTab === 'settlements' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
            <div>
              <h3 className="text-sm font-semibold text-paytm-navy">
                Bank Settlement Batches
              </h3>
              <p className="text-xs text-ink-secondary">
                Payouts transferred to registered bank account
              </p>
            </div>
            <SourceBadge source="SYNTHETIC_DEMO" size="sm" />
          </div>

          <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border text-xs text-ink-secondary">
            <strong>Honest Disclosure:</strong> Settlement API is production-only on Paytm. Payout verification is tested against the synthetic demo ledger.
          </div>

          {settlements.length === 0 ? (
            <EmptyState
              title="No settlement batches"
              description="Settlement batches generated at cut-off will appear here."
            />
          ) : (
            <div className="space-y-3">
              {settlements.map((batch) => (
                <Card key={batch.id} title={batch.batch_ref}>
                  <div className="space-y-2 pt-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-ink-secondary">Net Payout Amount:</span>
                      <span className="font-bold text-ink-primary">
                        ₹{parseFloat(batch.net || '0').toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-ink-secondary">Settlement Date:</span>
                      <span className="font-mono text-ink-primary">
                        {batch.expected_settlement_date ? `${new Date(batch.expected_settlement_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (${new Date(batch.date).toLocaleDateString([], { day: 'numeric', month: 'short' })})` : batch.date}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pt-2 border-t border-surface-divider">
                      <span className="text-[11px] text-ink-muted">
                        Settlement Status
                      </span>
                      <StatusChip status={batch.status === 'SETTLED' ? 'RESOLVED' : 'IN_PROGRESS'} />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: HELP & CHAT QUICK CATEGORIES */}
      {activeTab === 'help' && (
        <div className="space-y-4">
          <div className="pb-2 border-b border-surface-divider">
            <h3 className="text-sm font-semibold text-paytm-navy">
              Select Support Topic
            </h3>
            <p className="text-xs text-ink-secondary">
              Tap any category below to immediately start autonomous diagnosis
            </p>
          </div>

          {/* Category Chips */}
          <div className="flex flex-wrap gap-2">
            {categoryChips.map((chip) => (
              <button
                key={chip.label}
                type="button"
                onClick={() => triggerChat(chip.prompt)}
                className="inline-flex min-h-12 items-center px-4 py-2 rounded-xl text-xs font-semibold bg-surface-card border border-surface-border text-paytm-navy hover:bg-paytm-cyan-light hover:border-paytm-cyan/40 transition shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
              >
                {chip.label}
              </button>
            ))}
          </div>

          <div className="p-4 bg-paytm-cyan-light rounded-xl border border-paytm-cyan/30 text-xs text-paytm-navy">
            <p className="font-semibold">Autonomous OpsSaathi Support</p>
            <p className="mt-1 text-ink-secondary">
              Use voice or text below to resolve missing settlements, check fee schedules, or request supervisor escalation.
            </p>
          </div>
        </div>
      )}

      {/* Mobile Bottom Navigation Bar */}
      <BottomNav
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        badgeCounts={{
          help: cases.length > 0 ? cases.length : undefined,
        }}
      />

      {/* Case Details Modal */}
      {selectedCaseId && (
        <MerchantCaseModal
          isOpen={Boolean(selectedCaseId)}
          onClose={() => setSelectedCaseId(null)}
          caseId={selectedCaseId}
          token={token}
        />
      )}
    </div>
  )
}
