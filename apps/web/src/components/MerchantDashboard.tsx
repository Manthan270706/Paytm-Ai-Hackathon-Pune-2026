import { useState, FC } from 'react'
import {
  MerchantProfile,
  TransactionItem,
  SettlementBatchItem,
  SupportCaseItem,
} from '../types/api'
import { SourceBadge } from './SourceBadge'
import { MerchantCaseModal } from './MerchantCaseModal'
import {
  AlertCircle,
  ArrowUpRight,
  CreditCard,
  FileText,
  Sparkles,
} from 'lucide-react'

interface MerchantDashboardProps {
  profile: MerchantProfile | null
  transactions: TransactionItem[]
  settlements: SettlementBatchItem[]
  cases: SupportCaseItem[]
  discrepancy: string
  loading: boolean
  error: string | null
  token?: string
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
  onOpenChat,
}) => {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-slate-800/60 rounded-2xl border border-slate-700/60" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-32 bg-slate-800/60 rounded-2xl border border-slate-700/60" />
          <div className="h-32 bg-slate-800/60 rounded-2xl border border-slate-700/60" />
          <div className="h-32 bg-slate-800/60 rounded-2xl border border-slate-700/60" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-950/40 border border-rose-800/60 rounded-2xl text-rose-300 flex items-center gap-3">
        <AlertCircle className="h-6 w-6 text-rose-400 shrink-0" />
        <div>
          <h3 className="font-semibold text-sm">Failed to load dashboard data</h3>
          <p className="text-xs text-rose-300/80 mt-0.5">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Merchant Profile Header */}
      <div className="p-6 bg-slate-800/80 rounded-2xl border border-slate-700/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              {profile?.display_name || 'Two Bits Chai & Snacks'}
            </h2>
            <SourceBadge source={profile?.source_type || 'SYNTHETIC_DEMO'} />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Merchant ID: {profile?.id || '11111111-1111-1111-1111-111111111111'} • Phone: {profile?.masked_phone || '+91 98****1234'}
          </p>
        </div>

        <button
          onClick={() => onOpenChat('My ₹6,000 payment from yesterday is missing from settlement')}
          className="inline-flex items-center gap-2 bg-gradient-to-r from-sky-500 to-cyan-500 hover:from-sky-400 hover:to-cyan-400 text-slate-950 px-4 py-2.5 rounded-xl font-semibold text-sm shadow-lg shadow-sky-500/20 transition transform hover:-translate-y-0.5"
        >
          <Sparkles className="h-4 w-4" />
          <span>Ask OpsSaathi to Investigate</span>
        </button>
      </div>

      {/* Financial Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-5 bg-slate-800/60 rounded-2xl border border-slate-700/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Expected Net Settlement</span>
            <SourceBadge source="SYNTHETIC_DEMO" size="sm" />
          </div>
          <div className="text-2xl font-black text-white tracking-tight">₹15,000.00</div>
          <p className="text-[11px] text-slate-400">Total verified captures eligible for payout</p>
        </div>

        <div className="p-5 bg-slate-800/60 rounded-2xl border border-slate-700/60 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Observed in Bank Batch</span>
            <SourceBadge source="SYNTHETIC_DEMO" size="sm" />
          </div>
          <div className="text-2xl font-black text-slate-300 tracking-tight">₹9,000.00</div>
          <p className="text-[11px] text-slate-400">
            Credited via {settlements.length > 0 ? settlements[0].batch_ref : 'Batch #20261112_01'}
          </p>
        </div>

        <div className="p-5 bg-amber-950/30 rounded-2xl border border-amber-600/40 space-y-1 shadow-sm">
          <div className="flex items-center justify-between text-xs text-amber-300 font-medium">
            <span className="flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
              Missing Discrepancy
            </span>
            <span className="text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded">
              OVERDUE
            </span>
          </div>
          <div className="text-2xl font-black text-amber-400 tracking-tight">₹{discrepancy || '6,000.00'}</div>
          <p className="text-[11px] text-amber-300/80">Pending settlement re-sync approval</p>
        </div>
      </div>

      {/* Grid: Transactions and Open Cases */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Transactions Table */}
        <div className="p-6 bg-slate-800/60 rounded-2xl border border-slate-700/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-sky-400" />
              <h3 className="font-bold text-sm text-white">Recent Transactions</h3>
            </div>
            <span className="text-xs text-slate-400">{transactions.length} records</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 border-b border-slate-700/60 uppercase font-mono text-[10px]">
                <tr>
                  <th className="pb-2">Txn / Order</th>
                  <th className="pb-2">Amount</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2 text-right">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-slate-500">
                      No transactions found
                    </td>
                  </tr>
                ) : (
                  transactions.slice(0, 5).map((txn) => (
                    <tr key={txn.id} className="hover:bg-slate-700/20">
                      <td className="py-2.5 font-mono text-slate-300">
                        <div>{txn.provider_txn_id}</div>
                        <div className="text-[10px] text-slate-500">{txn.order_id}</div>
                      </td>
                      <td className="py-2.5 font-bold text-white">₹{txn.amount}</td>
                      <td className="py-2.5">
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {txn.status}
                        </span>
                      </td>
                      <td className="py-2.5 text-right">
                        <SourceBadge source={txn.source_type} size="sm" />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Support Cases & Batches */}
        <div className="p-6 bg-slate-800/60 rounded-2xl border border-slate-700/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-purple-400" />
              <h3 className="font-bold text-sm text-white">Operational Support Cases</h3>
            </div>
            <span className="text-xs text-slate-400">{cases.length} cases</span>
          </div>

          <div className="space-y-3">
            {cases.length === 0 ? (
              <div className="p-8 text-center text-slate-500 border border-dashed border-slate-700/60 rounded-xl text-xs">
                No active operational cases. Click "Ask OpsSaathi" to report an issue.
              </div>
            ) : (
              cases.map((sc) => (
                <div
                  key={sc.id}
                  onClick={() => setSelectedCaseId(sc.id)}
                  className="p-3.5 bg-slate-900/60 border border-slate-700/60 rounded-xl flex items-center justify-between gap-3 hover:border-slate-500 cursor-pointer transition"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-sky-400">{sc.case_number}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        {sc.status}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">v{sc.version}</span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 line-clamp-1">{sc.summary}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedCaseId(sc.id)
                    }}
                    className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
                    title="View Timeline"
                  >
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Merchant Case Detail & Timeline Modal */}
      <MerchantCaseModal
        isOpen={!!selectedCaseId}
        onClose={() => setSelectedCaseId(null)}
        caseId={selectedCaseId}
        token={token}
      />
    </div>
  )
}
