import { FC } from 'react'
import { TraceEvent } from '../types/api'
import { CheckCircle2, Terminal, ArrowRight } from 'lucide-react'

interface TracePanelProps {
  events: TraceEvent[]
  isOpen: boolean
  onClose: () => void
  runId: string | null
}

export const TracePanel: FC<TracePanelProps> = ({
  events,
  isOpen,
  onClose,
  runId,
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-96 bg-slate-950/95 backdrop-blur-xl border-l border-slate-800 z-50 p-6 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-sky-400" />
          <h3 className="font-bold text-sm text-white">Live Agent Trace (SSE)</h3>
        </div>
        <button
          onClick={onClose}
          className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-900 border border-slate-800"
        >
          Close
        </button>
      </div>

      <div className="py-2 text-[10px] text-slate-400 font-mono flex items-center justify-between">
        <span>Run ID: {runId ? `${runId.slice(0, 8)}...` : 'N/A'}</span>
        <span className="text-emerald-400 flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
          Live Stream
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 mt-2 text-xs">
        {events.length === 0 ? (
          <div className="py-16 text-center text-slate-500 font-mono text-xs">
            Waiting for agent execution events...
          </div>
        ) : (
          events.map((evt, idx) => {
            const isTerminal = evt.type === 'COMPLETED'
            return (
              <div
                key={evt.id || idx}
                className="p-3 bg-slate-900/80 rounded-xl border border-slate-800/80 font-mono space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-sky-300 font-semibold text-xs">
                    {isTerminal ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <ArrowRight className="h-3.5 w-3.5 text-sky-400" />
                    )}
                    <span>{evt.node || evt.tool || (isTerminal ? 'RUN FINISHED' : 'Node')}</span>
                  </div>

                  {evt.latency !== undefined && (
                    <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                      {evt.latency}s
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span
                    className={`font-semibold ${
                      evt.status === 'SUCCESS' || evt.status === 'COMPLETED'
                        ? 'text-emerald-400'
                        : evt.status === 'AWAITING_APPROVAL' || evt.status === 'REQUIRE_HUMAN_APPROVAL'
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {evt.status}
                  </span>
                  {evt.input_hash && (
                    <span className="text-slate-500 truncate max-w-[120px]" title={evt.input_hash}>
                      hash:{evt.input_hash.slice(0, 8)}
                    </span>
                  )}
                </div>

                {evt.output_ref && (
                  <details className="text-[10px] text-slate-400 mt-1 cursor-pointer">
                    <summary className="hover:text-slate-200">View payload ref</summary>
                    <pre className="mt-1 p-2 bg-slate-950 rounded border border-slate-800/60 overflow-x-auto text-[9px] text-slate-300">
                      {JSON.stringify(evt.output_ref, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
