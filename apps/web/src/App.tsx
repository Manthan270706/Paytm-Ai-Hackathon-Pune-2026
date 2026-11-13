import { useState, useEffect } from 'react'

interface HealthData {
  status: string
  environment: string
  llm_provider: string
  voice_provider: string
  demo_data_mode: boolean
  services: {
    api: string
    database: string
  }
}

export default function App() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/health')
      .then((res) => {
        if (!res.ok) throw new Error('API offline or unreachable')
        return res.json()
      })
      .then((data) => {
        setHealth(data.data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-6">
      <div className="max-w-xl w-full bg-slate-800 rounded-2xl shadow-xl border border-slate-700 p-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-10 w-10 rounded-xl bg-sky-500 flex items-center justify-center font-bold text-slate-950 text-xl shadow-lg shadow-sky-500/20">
            P
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">OpsSaathi AI</h1>
            <p className="text-xs text-sky-400 font-medium">
              Autonomous Merchant Operations Teammate (Track 3)
            </p>
          </div>
        </div>

        <div className="mt-6 p-4 rounded-xl bg-slate-900/60 border border-slate-700/60 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Backend API Status:</span>
            {loading ? (
              <span className="text-amber-400 animate-pulse font-medium">Checking...</span>
            ) : error ? (
              <span className="text-rose-400 font-medium">{error}</span>
            ) : (
              <span className="text-emerald-400 font-medium">Healthy ({health?.environment})</span>
            )}
          </div>

          {health && (
            <>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">LLM Provider:</span>
                <span className="text-slate-200 uppercase font-mono text-xs bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                  {health.llm_provider}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Voice Provider:</span>
                <span className="text-slate-200 uppercase font-mono text-xs bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                  {health.voice_provider}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Demo Data Mode:</span>
                <span className="text-emerald-400 text-xs font-semibold">Active</span>
              </div>
            </>
          )}
        </div>

        <div className="mt-6 flex justify-between items-center text-xs text-slate-500 border-t border-slate-700/60 pt-4">
          <span>Team Two Bits</span>
          <span>Paytm Build for India – Pune Finale</span>
        </div>
      </div>
    </div>
  )
}
