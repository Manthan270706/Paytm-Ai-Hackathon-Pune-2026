import { FC, useState } from 'react'
import { DiscrepancySummary } from '../types/api'
import { SourceBadge } from './SourceBadge'
import {
  FileSearch,
  Calculator,
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
    <div className="bg-surface-card border border-surface-border rounded-card p-4 space-y-3.5 shadow-sm font-sans text-ink-primary">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-paytm-navy" />
          <h4 className="font-semibold text-xs text-paytm-navy uppercase tracking-wider">
            Reconciliation Evidence
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <SourceBadge source={evidence.source_type} size="sm" />
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              isOverdue
                ? 'bg-status-rejected-bg text-status-rejected-text border-status-rejected-border'
                : isWithinSla
                ? 'bg-status-approval-bg text-status-approval-text border-status-approval-border'
                : 'bg-status-completed-bg text-status-completed-text border-status-completed-border'
            }`}
          >
            {evidence.reason_code}
          </span>
        </div>
      </div>

      {/* Financial Breakdown: The 3 Core Numbers */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2.5 bg-surface-subtle border border-surface-border rounded-lg">
          <span className="text-[10px] text-ink-secondary block font-medium">
            {evidence.metric_1_label || 'Expected Net'}
          </span>
          <span className="text-sm font-bold text-ink-primary font-mono mt-0.5 block">
            {evidence.metric_1_value || (evidence.expected_net ? `₹${evidence.expected_net}` : '—')}
          </span>
        </div>
        <div className="p-2.5 bg-surface-subtle border border-surface-border rounded-lg">
          <span className="text-[10px] text-ink-secondary block font-medium">
            {evidence.metric_2_label || 'Received Net'}
          </span>
          <span className="text-sm font-bold text-ink-primary font-mono mt-0.5 block">
            {evidence.metric_2_value || (evidence.observed_net ? `₹${evidence.observed_net}` : '—')}
          </span>
        </div>
        <div className="p-2.5 bg-status-approval-bg border border-status-approval-border rounded-lg">
          <span className="text-[10px] text-status-approval-text block font-semibold">
            {evidence.metric_3_label || 'Difference'}
          </span>
          <span className="text-sm font-bold text-status-approval-text font-mono mt-0.5 block">
            {evidence.metric_3_value || (evidence.discrepancy ? `₹${evidence.discrepancy}` : '—')}
          </span>
        </div>
      </div>

      {/* Records Checked */}
      {evidence.records_checked && evidence.records_checked.length > 0 && (
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-1.5 text-ink-secondary text-[11px] font-medium">
            <Database className="h-3 w-3 text-paytm-navy" />
            <span>Verified Records ({evidence.records_checked.length})</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {evidence.records_checked.map((recId, idx) => (
              <span
                key={idx}
                className="text-[10px] font-mono px-2 py-0.5 bg-surface-subtle text-ink-primary border border-surface-border rounded"
              >
                {recId.length > 20 ? `${recId.slice(0, 10)}...${recId.slice(-6)}` : recId}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Calculation Trace Accordion (Collapsed by Default) */}
      {evidence.calculation_trace && (
        <div className="border border-surface-border rounded-lg bg-surface-canvas overflow-hidden text-xs">
          <button
            type="button"
            onClick={() => setShowTraceDetails((prev) => !prev)}
            className="w-full flex items-center justify-between p-2.5 text-ink-secondary hover:text-ink-primary transition text-left min-h-10"
          >
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-paytm-navy">
              <Calculator className="h-3.5 w-3.5 text-paytm-navy" />
              <span>Calculation Details & Trace</span>
            </div>
            {showTraceDetails ? (
              <ChevronUp className="h-3.5 w-3.5 text-ink-secondary" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-ink-secondary" />
            )}
          </button>

          {showTraceDetails && (
            <div className="p-2.5 pt-0 border-t border-surface-divider font-mono text-[10px] text-ink-primary space-y-1.5">
              <pre className="p-2 bg-surface-card rounded border border-surface-border overflow-x-auto text-ink-primary">
                {JSON.stringify(evidence.calculation_trace, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Next Action Note */}
      {evidence.next_action && (
        <div className="flex items-start gap-2 p-2.5 bg-paytm-cyan-light border border-paytm-cyan/30 rounded-lg text-paytm-navy text-[11px]">
          <ArrowRight className="h-3.5 w-3.5 text-paytm-navy shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-paytm-navy">Next Step: </span>
            <span className="text-ink-secondary">{evidence.next_action}</span>
          </div>
        </div>
      )}

      {/* Footer Info & Actions */}
      <div className="pt-2 border-t border-surface-divider flex items-center justify-between text-[11px]">
        {activeCaseId ? (
          <span className="text-ink-secondary flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5 text-status-completed-text" />
            Ticket Ref:{' '}
            <strong className="text-ink-primary font-mono">
              #{evidence.case_number || (activeCaseId.startsWith('CASE-') ? activeCaseId : activeCaseId.slice(0, 8))}
            </strong>
          </span>
        ) : (
          <span className="text-ink-muted italic">No ticket created</span>
        )}

        {onOpenTrace && (
          <button
            type="button"
            onClick={onOpenTrace}
            className="flex items-center gap-1 text-paytm-navy hover:underline font-medium transition"
          >
            <Terminal className="h-3 w-3" />
            <span>Technical Details</span>
          </button>
        )}
      </div>
    </div>
  )
}
