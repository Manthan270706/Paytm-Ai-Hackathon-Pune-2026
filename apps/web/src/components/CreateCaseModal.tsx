import { useState, FC } from 'react'
import { PlusCircle, X, Layers, AlertCircle } from 'lucide-react'
import { Button } from './Button'

interface CreateCaseModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateCase: (data: {
    category: string
    priority: string
    queue: string
    summary: string
  }) => Promise<void>
}

const CATEGORIES = [
  { id: 'SETTLEMENT_MISMATCH', label: 'Settlement Mismatch' },
  { id: 'REFUND_DISPUTE', label: 'Refund Dispute / Double Debit' },
  { id: 'FEE_OVERCHARGE', label: 'MDR / Fee Schedule Overcharge' },
  { id: 'HARDWARE_DIAGNOSTICS', label: 'Soundbox / QR Hardware Diagnostics' },
  { id: 'PAYOUT_DELAY', label: 'Delayed Payout / Bank Holiday Hold' },
]

const QUEUES = [
  { id: 'SETTLEMENT_OPS', label: 'Settlement Operations' },
  { id: 'SETTLEMENTS', label: 'Settlements & Payouts' },
  { id: 'TECH_SUPPORT', label: 'Technical Support (IoT / Soundbox)' },
  { id: 'ESCALATIONS', label: 'Tier-2 Critical Escalations' },
]

const PRIORITIES = [
  { id: 'P0', label: 'P0 - Critical (SLA Breach / Blocked Funds)' },
  { id: 'P1', label: 'P1 - High (Discrepancy > ₹5,000)' },
  { id: 'P2', label: 'P2 - Medium (Routine Ledger Discrepancy)' },
  { id: 'P3', label: 'P3 - Low (Informational / Minor Hardware)' },
]

const QUICK_TEMPLATES = [
  {
    category: 'SETTLEMENT_MISMATCH',
    queue: 'SETTLEMENT_OPS',
    priority: 'P1',
    summary: 'Missing ₹3,500.00 from settlement batch BATCH_20261113_02 (overdue SLA)',
  },
  {
    category: 'REFUND_DISPUTE',
    queue: 'SETTLEMENTS',
    priority: 'P2',
    summary: 'Customer refund for Order #ORD_20261112_08 debited twice (₹1,500.00) on ledger',
  },
  {
    category: 'FEE_OVERCHARGE',
    queue: 'SETTLEMENT_OPS',
    priority: 'P2',
    summary: 'MDR fee rate mismatch: 2.15% charged on RuPay credit batch instead of agreed 1.20%',
  },
  {
    category: 'HARDWARE_DIAGNOSTICS',
    queue: 'TECH_SUPPORT',
    priority: 'P3',
    summary: 'Paytm Soundbox 4G audio announcement delayed by 40 seconds during rush hours',
  },
  {
    category: 'PAYOUT_DELAY',
    queue: 'ESCALATIONS',
    priority: 'P0',
    summary: 'T+1 bank holiday hold exceeded 48h SLA for weekend batch BATCH_20261110_02 (₹24,000.00)',
  },
]

export const CreateCaseModal: FC<CreateCaseModalProps> = ({
  isOpen,
  onClose,
  onCreateCase,
}) => {
  const [category, setCategory] = useState('SETTLEMENT_MISMATCH')
  const [queue, setQueue] = useState('SETTLEMENT_OPS')
  const [priority, setPriority] = useState('P1')
  const [summary, setSummary] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!summary.trim()) {
      setError('Please provide a summary for the support case.')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      await onCreateCase({
        category,
        queue,
        priority,
        summary: summary.trim(),
      })
      setSummary('')
      onClose()
    } catch (err: any) {
      setError(err?.message || 'Failed to create case')
    } finally {
      setIsSubmitting(false)
    }
  }

  const applyTemplate = (t: (typeof QUICK_TEMPLATES)[0]) => {
    setCategory(t.category)
    setQueue(t.queue)
    setPriority(t.priority)
    setSummary(t.summary)
    setError(null)
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-case-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/50 backdrop-blur-sm animate-in fade-in duration-200 font-sans"
    >
      <div className="bg-surface-card border border-surface-border rounded-2xl max-w-xl w-full p-6 shadow-xl space-y-5 text-ink-primary">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-surface-divider pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-paytm-cyan-light border border-paytm-cyan/30 text-paytm-navy">
              <PlusCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 id="create-case-title" className="text-base font-bold text-paytm-navy tracking-tight">
                Create Support Case
              </h3>
              <p className="text-xs text-ink-secondary">
                Register a new operational investigation ticket across queues
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close dialog"
            className="flex items-center justify-center w-10 h-10 min-h-12 min-w-12 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-surface-subtle transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Quick Scenario Templates */}
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-ink-secondary flex items-center gap-1">
            <Layers className="h-3 w-3 text-paytm-navy" />
            Quick Presets
          </span>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_TEMPLATES.map((tpl, i) => (
              <button
                key={i}
                type="button"
                onClick={() => applyTemplate(tpl)}
                className="text-[11px] px-2.5 py-1 bg-surface-subtle hover:bg-surface-border text-ink-primary border border-surface-border rounded-lg transition"
              >
                {tpl.category.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-status-rejected-bg border border-status-rejected-border rounded-xl text-xs text-status-rejected-text flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Category */}
            <div>
              <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-surface-subtle border border-surface-border rounded-xl p-2.5 text-xs text-ink-primary outline-none focus:border-paytm-cyan transition"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Queue */}
            <div>
              <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                Assigned Queue
              </label>
              <select
                value={queue}
                onChange={(e) => setQueue(e.target.value)}
                className="w-full bg-surface-subtle border border-surface-border rounded-xl p-2.5 text-xs text-ink-primary outline-none focus:border-paytm-cyan transition"
              >
                {QUEUES.map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-[11px] font-semibold text-ink-primary mb-1">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full bg-surface-subtle border border-surface-border rounded-xl p-2.5 text-xs text-ink-primary outline-none focus:border-paytm-cyan transition"
            >
              {PRIORITIES.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* Summary */}
          <div>
            <label className="block text-[11px] font-semibold text-ink-primary mb-1">
              Case Summary &amp; Details <span className="text-status-rejected-text">*</span>
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Describe the transaction reference, amounts, or discrepancy in detail..."
              rows={3}
              className="w-full bg-surface-subtle border border-surface-border rounded-xl p-2.5 text-xs text-ink-primary placeholder:text-ink-muted outline-none focus:border-paytm-cyan transition"
            />
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-divider">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs min-h-10 px-4"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isSubmitting}
              className="text-xs min-h-10 px-4 gap-2"
            >
              <PlusCircle className={`h-4 w-4 ${isSubmitting ? 'animate-spin' : ''}`} />
              <span>{isSubmitting ? 'Creating Case...' : 'Create Case'}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
