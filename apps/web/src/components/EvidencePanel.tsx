import { FC, useState } from 'react'
import { DiscrepancySummary } from '../types/api'
import { SourceBadge } from './SourceBadge'
import {
  FileSearch,
  Calculator,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Terminal,
  Database,
} from 'lucide-react'

interface EvidencePanelProps {
  evidence: DiscrepancySummary
  activeCaseId?: string | null
  onOpenTrace?: () => void
}

export const EvidencePanel: FC<EvidencePanelProps> = ({
  evidence,
  activeCaseId,
  onOpenTrace,
}) => {
  const [showTraceDetails, setShowTraceDetails] = useState(false)

  const isOverdue = evidence.reason_code === 'OVERDUE'
  const isWithinSla = evidence.reason_code === 'WITHIN_SLA_PENDING'

  return (
    <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-3.5 shadow-lg font-sans">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-sky-400" />
          <h4 className="font-bold text-xs text-white uppercase tracking-wider">
            Reconciliation Evidence & Investigation
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <SourceBadge source={evidence.source_type} size="sm" />
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              isOverdue
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                : isWithinSla
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            }`}
          >
            {evidence.reason_code}
          </span>
        </div>
      </div>

      {/* Financial Breakdown Grid */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2.5 bg-slate-900/80 border border-slate-800/80 rounded-lg">
          <span className="text-[10px] text-slate-400 block font-mono">{evidence.metric_1_label || 'Expected Net'}</span>
          <span className="text-sm font-bold text-white font-mono">
            {evidence.metric_1_value || (evidence.expected_net ? `₹${evidence.expected_net}` : '—')}
          </span>
        </div>
        <div className="p-2.5 bg-slate-900/80 border border-slate-800/80 rounded-lg">
          <span className="text-[10px] text-slate-400 block font-mono">{evidence.metric_2_label || 'Observed Net'}</span>
          <span className="text-sm font-bold text-slate-300 font-mono">
            {evidence.metric_2_value || (evidence.observed_net ? `₹${evidence.observed_net}` : '—')}
          </span>
        </div>
        <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg">
          <span className="text-[10px] text-amber-400 block font-mono">{evidence.metric_3_label || 'Discrepancy'}</span>
          <span className="text-sm font-bold text-amber-300 font-mono">
            {evidence.metric_3_value || (evidence.discrepancy ? `₹${evidence.discrepancy}` : '—')}
          </span>
        </div>
      </div>

      {/* Records Checked */}
      {evidence.records_checked && evidence.records_checked.length > 0 && (
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-semibold">
            <Database className="h-3 w-3 text-sky-400" />
            <span>Records Checked ({evidence.records_checked.length})</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {evidence.records_checked.map((recId, idx) => (
              <span
                key={idx}
                className="text-[10px] font-mono px-2 py-0.5 bg-slate-900 text-slate-300 border border-slate-800 rounded"
              >
                {recId.length > 20 ? `${recId.slice(0, 10)}...${recId.slice(-6)}` : recId}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Calculation Trace Accordion */}
      {evidence.calculation_trace && (
        <div className="border border-slate-800/80 rounded-lg bg-slate-900/40 overflow-hidden text-xs">
          <button
            onClick={() => setShowTraceDetails((prev) => !prev)}
            className="w-full flex items-center justify-between p-2.5 text-slate-300 hover:text-white transition text-left"
          >
            <div className="flex items-center gap-1.5 text-[11px] font-semibold">
              <Calculator className="h-3 w-3 text-sky-400" />
              <span>Deterministic Calculation Trace</span>
            </div>
            {showTraceDetails ? (
              <ChevronUp className="h-3.5 w-3.5 text-slate-400" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            )}
          </button>

          {showTraceDetails && (
            <div className="p-2.5 pt-0 border-t border-slate-800/60 font-mono text-[10px] text-slate-300 space-y-1.5">
              <pre className="p-2 bg-slate-950 rounded border border-slate-800/80 overflow-x-auto text-slate-300">
                {JSON.stringify(evidence.calculation_trace, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Audit Limitations & Next Action */}
      <div className="space-y-2 text-xs">
        {evidence.limitations && (
          <div className="flex items-start gap-2 p-2 bg-slate-900/50 border border-slate-800 rounded-lg text-slate-400 text-[11px]">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-300">Limitation: </span>
              {evidence.limitations}
            </div>
          </div>
        )}

        {evidence.next_action && (
          <div className="flex items-start gap-2 p-2 bg-sky-950/20 border border-sky-800/30 rounded-lg text-sky-300 text-[11px]">
            <ArrowRight className="h-3.5 w-3.5 text-sky-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-white">Next Action: </span>
              {evidence.next_action}
            </div>
          </div>
        )}
      </div>

      {/* Footer Info & Actions */}
      <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
        {activeCaseId ? (
          <span className="text-slate-400 flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            Bound to Case:{' '}
            <strong className="text-white">
              #{evidence.case_number || (activeCaseId.startsWith('CASE-') ? activeCaseId : activeCaseId.slice(0, 8))}
            </strong>
          </span>
        ) : (
          <span className="text-slate-500 italic">No case created yet</span>
        )}

        {onOpenTrace && (
          <button
            onClick={onOpenTrace}
            className="flex items-center gap-1 text-sky-400 hover:text-sky-300 font-mono font-medium transition"
          >
            <Terminal className="h-3 w-3" />
            <span>Inspect SSE Trace</span>
          </button>
        )}
      </div>
    </div>
  )
}
