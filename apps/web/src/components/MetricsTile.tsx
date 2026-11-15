import { FC } from 'react'
import { OutcomeMetrics } from '../types/api'
import { Clock, Zap, CheckCircle2, RotateCcw, ShieldCheck } from 'lucide-react'

interface MetricsTileProps {
  metrics: OutcomeMetrics | null
  isLoading?: boolean
  onRefresh?: () => void
}

export const MetricsTile: FC<MetricsTileProps> = ({ metrics, isLoading = false, onRefresh }) => {
  if (!metrics) return null

  return (
    <div className="bg-surface-card border border-surface-border rounded-card p-4 shadow-sm space-y-3 font-sans text-ink-primary">
      <div className="flex items-center justify-between pb-2 border-b border-surface-divider">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-paytm-navy" />
          <h3 className="text-sm font-semibold text-paytm-navy uppercase tracking-wider">
            Operational Outcome Metrics
          </h3>
        </div>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isLoading}
            className="text-xs text-paytm-navy hover:bg-surface-subtle flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-surface-border transition disabled:opacity-50"
            title="Refresh outcome metrics from backend"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Metric 1: Time to First Response */}
        <div className="bg-surface-subtle border border-surface-border rounded-lg p-3">
          <div className="flex items-center justify-between text-ink-secondary mb-1">
            <span className="text-[11px] font-medium">First Response</span>
            <Clock className="w-3.5 h-3.5 text-paytm-navy" />
          </div>
          <div className="text-xl font-bold text-ink-primary tracking-tight font-mono">
            {metrics.time_to_first_response_seconds}s
          </div>
          <div className="text-[10px] text-ink-muted mt-0.5">
            Instant AI triage
          </div>
        </div>

        {/* Metric 2: Time to Verified Resolution */}
        <div className="bg-surface-subtle border border-surface-border rounded-lg p-3">
          <div className="flex items-center justify-between text-ink-secondary mb-1">
            <span className="text-[11px] font-medium">Resolution Time</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-status-completed-text" />
          </div>
          <div className="text-xl font-bold text-ink-primary tracking-tight font-mono">
            {metrics.time_to_verified_resolution_minutes}m
          </div>
          <div className="text-[10px] text-status-completed-text mt-0.5 font-medium">
            vs 24h manual SLA
          </div>
        </div>

        {/* Metric 3: Straight Through Processing (STP) Rate */}
        <div className="bg-surface-subtle border border-surface-border rounded-lg p-3">
          <div className="flex items-center justify-between text-ink-secondary mb-1">
            <span className="text-[11px] font-medium">STP Deflection</span>
            <Zap className="w-3.5 h-3.5 text-paytm-navy" />
          </div>
          <div className="text-xl font-bold text-paytm-navy tracking-tight font-mono">
            {metrics.straight_through_processing_rate_percent}%
          </div>
          <div className="text-[10px] text-ink-muted mt-0.5">
            Automated verification
          </div>
        </div>

        {/* Metric 4: Total Cases Handled */}
        <div className="bg-surface-subtle border border-surface-border rounded-lg p-3">
          <div className="flex items-center justify-between text-ink-secondary mb-1">
            <span className="text-[11px] font-medium">Cases Handled</span>
            <ShieldCheck className="w-3.5 h-3.5 text-status-completed-text" />
          </div>
          <div className="text-xl font-bold text-status-completed-text tracking-tight font-mono">
            {metrics.total_cases_handled}
          </div>
          <div className="text-[10px] text-status-completed-text mt-0.5 font-medium">
            {metrics.repeat_explanations_avoided} repeat issues avoided
          </div>
        </div>
      </div>
    </div>
  )
}
