import { FC } from 'react'
import { IntegrationHealth } from '../types/api'
import {
  Activity,
  X,
  Database,
  Cpu,
  Mic,
  CreditCard,
  Building,
  ShieldCheck,
} from 'lucide-react'

interface IntegrationHealthModalProps {
  isOpen: boolean
  onClose: () => void
  health: IntegrationHealth | null
  isLoading?: boolean
}

export const IntegrationHealthModal: FC<IntegrationHealthModalProps> = ({
  isOpen,
  onClose,
  health,
  isLoading = false,
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white tracking-tight">
                  Integration & System Health
                </h3>
                <span className="text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  OPERATIONAL
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Active provider adapters, fallback chains, and security boundaries
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4">
          {isLoading && !health ? (
            <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
              <Activity className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-xs">Fetching active adapter health...</p>
            </div>
          ) : health ? (
            <>
              {/* Security Banner */}
              <div className="bg-slate-950/60 border border-emerald-500/20 rounded-2xl p-4 flex items-center gap-3">
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                <div className="text-xs text-slate-300">
                  <span className="font-bold text-white">Zero Secret Exposure:</span> All
                  merchant keys, Groq/Gemini API tokens, and Sarvam credentials reside strictly in
                  isolated server-side environments. No secrets are logged or transmitted to the client.
                </div>
              </div>

              {/* Grid of Adapters */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {/* 1. Database & Verifier */}
                <div className="bg-slate-950/50 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-white">
                      <Database className="w-4 h-4 text-cyan-400" />
                      <span>Database & Verifier</span>
                    </div>
                    <span className="text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full">
                      {health.services.database}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Service:</span>
                      <span className="text-slate-300 font-medium">Async SQLAlchemy Engine</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Verifier Role:</span>
                      <span className="text-emerald-400 font-mono text-[11px]">
                        opssaathi_verifier (READ ONLY)
                      </span>
                    </div>
                  </div>
                </div>

                {/* 2. Payment Integration */}
                <div className="bg-slate-950/50 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-white">
                      <CreditCard className="w-4 h-4 text-cyan-400" />
                      <span>Paytm Payment Provider</span>
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        health.payment_provider.status === 'AVAILABLE'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }`}
                    >
                      {health.payment_provider.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Active Origin:</span>
                      <span className="text-slate-200 font-mono text-[11px]">
                        {health.payment_provider.active}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Environment:</span>
                      <span className="text-slate-300 font-medium capitalize">
                        {health.payment_provider.environment}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 3. LLM Intelligence & Replay */}
                <div className="bg-slate-950/50 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-white">
                      <Cpu className="w-4 h-4 text-purple-400" />
                      <span>LLM & Replay Engine</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-bold uppercase bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded-full">
                        {health.llm_provider}
                      </span>
                      <span className="text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        ONLINE
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Provider Status:</span>
                      <span className="text-emerald-400 font-semibold text-[11px]">
                        {health.llm_provider === 'groq'
                          ? 'Active (Groq LPU / Local LLM)'
                          : health.llm_provider === 'gemini'
                          ? 'Active (Google Gemini 3.5 Flash)'
                          : `Active (${health.llm_provider.toUpperCase()})`}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Replay Mode:</span>
                      <span
                        className={`font-bold text-[11px] ${
                          health.demo_deterministic ? 'text-amber-400' : 'text-slate-300'
                        }`}
                      >
                        {health.demo_deterministic ? 'Enabled (Deterministic Cache)' : 'Disabled (Live API Calls)'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Fallback Chain:</span>
                      <span className="text-slate-300 font-medium text-[11px]">
                        Local LLM → Groq Cloud → Cache → Mock
                      </span>
                    </div>
                  </div>
                </div>

                {/* 4. Voice Engine (Sarvam + Browser) */}
                <div className="bg-slate-950/50 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-white">
                      <Mic className="w-4 h-4 text-pink-400" />
                      <span>Voice Engine</span>
                    </div>
                    <span className="text-[10px] font-bold uppercase bg-pink-500/10 text-pink-400 px-2 py-0.5 rounded-full">
                      {health.voice_provider}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Multilingual:</span>
                      <span className="text-slate-300 font-medium">English, Hindi, Marathi</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Fallback:</span>
                      <span className="text-slate-300 font-medium">Browser Speech → Text Chat</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Settlement Ops Note */}
              <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-3.5 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-slate-300">
                  <Building className="w-4 h-4 text-amber-400" />
                  <span>Settlement Ops System Adapter:</span>
                </div>
                <div className="font-mono text-[11px] text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
                  Mock SettlementOps Adapter (Policy Threshold ₹5,000.00)
                </div>
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-red-400 text-xs">
              Unable to load integration health. Ensure API server is reachable.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
