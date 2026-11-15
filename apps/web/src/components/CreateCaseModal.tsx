import { useState, FC } from 'react'
import { PlusCircle, X, Layers, AlertCircle } from 'lucide-react'

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5 text-slate-200">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <PlusCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Create Support Case</h3>
              <p className="text-xs text-slate-400">
                Register a new operational investigation ticket across queues
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Quick Scenario Templates */}
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Layers className="h-3 w-3 text-sky-400" />
            Quick Scenario Presets
          </span>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_TEMPLATES.map((tpl, i) => (
              <button
                key={i}
                type="button"
                onClick={() => applyTemplate(tpl)}
                className="text-[10px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700/80 text-slate-300 border border-slate-700 rounded-lg transition"
              >
                {tpl.category.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Category */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-slate-200 outline-none focus:border-sky-500 transition"
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
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Assigned Queue
              </label>
              <select
                value={queue}
                onChange={(e) => setQueue(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-slate-200 outline-none focus:border-sky-500 transition"
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
            <label className="block text-[11px] font-semibold text-slate-300 mb-1">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-slate-200 outline-none focus:border-sky-500 transition"
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
            <label className="block text-[11px] font-semibold text-slate-300 mb-1">
              Case Summary &amp; Details <span className="text-rose-400">*</span>
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Describe the transaction reference, amounts, or discrepancy in detail..."
              rows={3}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-slate-200 placeholder:text-slate-500 outline-none focus:border-sky-500 transition"
            />
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-sky-500 to-cyan-500 hover:from-sky-400 hover:to-cyan-400 text-slate-950 font-bold px-5 py-2.5 rounded-xl text-xs transition shadow-lg shadow-sky-500/25 disabled:opacity-50"
            >
              <PlusCircle className={`h-4 w-4 ${isSubmitting ? 'animate-spin' : ''}`} />
              <span>{isSubmitting ? 'Creating Case...' : 'Create Case'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
