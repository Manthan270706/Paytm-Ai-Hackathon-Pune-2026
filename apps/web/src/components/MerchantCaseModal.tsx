import { useState, useEffect, FC } from 'react'
import { CaseDetail } from '../types/api'
import { API_BASE } from '../config'
import {
  X,
  FileText,
  Clock,
  User,
  CheckCircle2,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react'

interface MerchantCaseModalProps {
  isOpen: boolean
  onClose: () => void
  caseId: string | null
  token: string
}

export const MerchantCaseModal: FC<MerchantCaseModalProps> = ({
  isOpen,
  onClose,
  caseId,
  token,
}) => {
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !caseId) {
      setCaseDetail(null)
      return
    }

    const fetchCase = async () => {
      try {
        setLoading(true)
        setError(null)
        const res = await fetch(`${API_BASE}/cases/${caseId}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error('Failed to load case detail')
        const data = await res.json()
        setCaseDetail(data.data)
      } catch (err: any) {
        setError(err.message || 'Error loading case')
      } finally {
        setLoading(false)
      }
    }

    fetchCase()
  }, [isOpen, caseId, token])

  if (!isOpen || !caseId) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5 text-slate-200 max-h-[85vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white font-mono">
                  {caseDetail?.case_number || 'Case Detail'}
                </h3>
                {caseDetail && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                      caseDetail.status === 'RESOLVED'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : caseDetail.status === 'VERIFYING'
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                        : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    }`}
                  >
                    {caseDetail.status}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Merchant Operations Support Case Timeline
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="overflow-y-auto space-y-4 pr-1 flex-1 text-xs">
          {loading ? (
            <div className="py-12 text-center text-slate-500">Loading case timeline...</div>
          ) : error ? (
            <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300">
              {error}
            </div>
          ) : caseDetail ? (
            <>
              {/* Case Summary */}
              <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <div className="text-slate-300 font-medium leading-relaxed">
                  {caseDetail.summary}
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-900">
                  <div>
                    Category: <span className="text-slate-300">{caseDetail.category}</span>
                  </div>
                  <div>
                    Assigned Queue: <span className="text-purple-400">{caseDetail.queue}</span>
                  </div>
                </div>
              </div>

              {/* Status Banners */}
              {caseDetail.status === 'RESOLVED' && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-center gap-2.5">
                  <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0" />
                  <div>
                    <span className="font-bold">Verified Resolution Confirmed: </span>
                    Case has been resolved and verified by independent read-only audit verifier (opssaathi_verifier).
                  </div>
                </div>
              )}
              {caseDetail.status === 'VERIFYING' && (
                <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-xl text-xs text-sky-300 flex items-center gap-2.5">
                  <ShieldCheck className="h-5 w-5 text-sky-400 shrink-0" />
                  <div>
                    <span className="font-bold">Independent Verification In Progress: </span>
                    Remedial adjustments applied; undergoing cryptographic ledger verification.
                  </div>
                </div>
              )}
              {caseDetail.status === 'AWAITING_APPROVAL' && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 flex items-center gap-2.5">
                  <ShieldCheck className="h-5 w-5 text-amber-400 shrink-0" />
                  <div>
                    <span className="font-bold">Supervisor Authorization Gated: </span>
                    Resolution exceeds autonomous threshold and is awaiting supervisor approval before execution.
                  </div>
                </div>
              )}

              {/* Merchant-Visible Timeline */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between pb-1 border-b border-slate-800 text-[11px] text-slate-400 font-semibold">
                  <span>Case Activity &amp; Status Updates</span>
                  <span>{caseDetail.timeline?.length || 0} updates</span>
                </div>

                {!caseDetail.timeline || caseDetail.timeline.length === 0 ? (
                  <div className="py-6 text-center text-slate-500 text-xs">
                    No status updates recorded yet.
                  </div>
                ) : (
                  <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
                    {caseDetail.timeline.map((ev) => (
                      <div key={ev.id} className="relative flex items-start gap-3 pl-1">
                        <div
                          className={`h-6 w-6 rounded-full flex items-center justify-center shrink-0 border z-10 ${
                            ev.event_type === 'VERIFICATION_COMPLETED' ||
                            ev.event_type === 'CASE_RESOLVED'
                              ? 'bg-emerald-950 border-emerald-500 text-emerald-400'
                              : 'bg-sky-950 border-sky-500 text-sky-400'
                          }`}
                        >
                          {ev.event_type === 'VERIFICATION_COMPLETED' ||
                          ev.event_type === 'CASE_RESOLVED' ? (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-sky-300">
                              {ev.event_type}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {new Date(ev.created_at).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>

                          <div className="text-[11px] text-slate-400 flex items-center gap-1">
                            <User className="h-3 w-3 text-slate-500" />
                            <span>Actor:</span>
                            <strong className="text-slate-300 font-medium">{ev.actor}</strong>
                          </div>

                          {ev.payload && Object.keys(ev.payload).length > 0 && (
                            <div className="mt-1 pt-1 font-mono text-[10px] text-slate-400 bg-slate-900/40 p-2 rounded-lg space-y-1 overflow-hidden">
                              {Object.entries(ev.payload).map(([k, v]) => (
                                <div key={k} className="break-words [overflow-wrap:anywhere] leading-relaxed">
                                  <span className="text-slate-500 font-semibold">{k}:</span>{' '}
                                  <span className="text-slate-300 break-words [overflow-wrap:anywhere]">
                                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="flex justify-end pt-3 border-t border-slate-800 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
