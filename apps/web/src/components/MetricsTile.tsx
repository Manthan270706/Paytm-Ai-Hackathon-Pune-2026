import { FC } from 'react'
import { OutcomeMetrics } from '../types/api'
import { Clock, Zap, CheckCircle2, RotateCcw, AlertTriangle, MessageSquare } from 'lucide-react'

interface MetricsTileProps {
  metrics: OutcomeMetrics | null
  isLoading?: boolean
  onRefresh?: () => void
}

export const MetricsTile: FC<MetricsTileProps> = ({ metrics, isLoading = false, onRefresh }) => {
  if (!metrics) return null

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-bold text-white tracking-wide uppercase">
            Operational Outcome Metrics
          </h3>
          <span className="text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded-full">
            REAL-TIME FROM CASE EVENTS
          </span>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 transition disabled:opacity-50"
            title="Refresh outcome metrics from backend"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {/* Metric 1: Time to First Response */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-medium">First Response</span>
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-black text-white tracking-tight">
            {metrics.time_to_first_response_seconds}s
          </div>
          <div className="text-[10px] text-cyan-400/80 font-medium mt-1">
            Instant AI triage
          </div>
        </div>

        {/* Metric 2: Time to Verified Resolution */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-medium">Resolution Time</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-black text-emerald-400 tracking-tight">
            {metrics.time_to_verified_resolution_minutes}m
          </div>
          <div className="text-[10px] text-emerald-400/80 font-medium mt-1">
            Independent verification PASS
          </div>
        </div>

        {/* Metric 3: Straight-Through Processing */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-medium">STP Rate</span>
            <Zap className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-black text-amber-400 tracking-tight">
            {metrics.straight_through_processing_rate_percent}%
          </div>
          <div className="text-[10px] text-slate-400 font-medium mt-1">
            Straight-through handling
          </div>
        </div>

        {/* Metric 4: Handled vs Escalated */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-medium">Cases Handled</span>
            <AlertTriangle className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-xl font-black text-purple-300 tracking-tight">
            {metrics.total_cases_handled}
          </div>
          <div className="text-[10px] text-purple-400/80 font-medium mt-1">
            {metrics.total_cases_escalated} escalated to human
          </div>
        </div>

        {/* Metric 5: Repeat Explanations Avoided */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-medium">Repeat Explanations</span>
            <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-xl font-black text-indigo-300 tracking-tight">
            {metrics.repeat_explanations_avoided}
          </div>
          <div className="text-[10px] text-indigo-400/80 font-medium mt-1">
            Channel continuity preserved
          </div>
        </div>
      </div>
    </div>
  )
}
