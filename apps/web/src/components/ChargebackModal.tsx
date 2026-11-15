import React, { useState } from 'react'
import { ChargebackDefensePacket } from '../types/api'

interface ChargebackModalProps {
  isOpen: boolean
  packet: ChargebackDefensePacket | null
  isLoading?: boolean
  onClose: () => void
  onSubmitToNpci?: () => void
}

export const ChargebackModal: React.FC<ChargebackModalProps> = ({
  isOpen,
  packet,
  isLoading = false,
  onClose,
  onSubmitToNpci,
}) => {
  const [activeTab, setActiveTab] = useState<'docket' | 'hardware' | 'npci'>('docket')
  const [copied, setCopied] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  if (!isOpen) return null

  const handleCopy = () => {
    if (packet) {
      navigator.clipboard.writeText(packet.arbitration_docket_markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleSubmit = () => {
    setIsSubmitted(true)
    if (onSubmitToNpci) onSubmitToNpci()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-card border border-surface-border rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-surface-canvas">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-status-verifying-bg border border-status-verifying-border flex items-center justify-center text-paytm-navy">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-ink-primary">Autonomous Chargeback Defense Builder</h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-paytm-cyan/15 text-paytm-navy border border-paytm-cyan/30">
                  Paytm Pi Risk Agent
                </span>
              </div>
              <p className="text-xs text-ink-secondary">
                Auto-compiled arbitration packet for NPCI & Card Network Dispute Portals
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-ink-muted hover:text-ink-primary transition-colors p-1 rounded-lg"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Loading State */}
        {isLoading || !packet ? (
          <div className="p-8 text-center">
            <div className="animate-spin w-8 h-8 border-2 border-paytm-cyan border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm font-medium text-ink-secondary">Compiling transaction ledger, Soundbox chime logs & NPCI RRN...</p>
          </div>
        ) : (
          <>
            {/* Summary Bar */}
            <div className="px-6 py-3 bg-surface-canvas/50 border-b border-surface-border flex flex-wrap items-center justify-between gap-3 text-xs">
              <div>
                <span className="text-ink-muted">Case / Order: </span>
                <strong className="text-ink-primary font-mono">{packet.case_number}</strong> / <strong className="font-mono">{packet.order_id}</strong>
              </div>
              <div>
                <span className="text-ink-muted">Disputed Amount: </span>
                <strong className="text-status-rejected-text font-bold">₹{packet.disputed_amount}</strong>
              </div>
              <div>
                <span className="text-ink-muted">Submission Deadline: </span>
                <strong className="text-ink-primary">{packet.submission_deadline}</strong>
              </div>
              <div>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-status-verifying-bg text-status-verifying-text border border-status-verifying-border">
                  {isSubmitted ? 'SUBMITTED TO NPCI' : packet.status}
                </span>
              </div>
            </div>

            {/* Nav Tabs */}
            <div className="flex border-b border-surface-border px-6 pt-2 gap-4 text-xs font-medium">
              <button
                onClick={() => setActiveTab('docket')}
                className={`pb-2.5 transition-colors border-b-2 ${
                  activeTab === 'docket'
                    ? 'border-paytm-cyan text-paytm-navy font-bold'
                    : 'border-transparent text-ink-secondary hover:text-ink-primary'
                }`}
              >
                Arbitration Defense Docket
              </button>
              <button
                onClick={() => setActiveTab('hardware')}
                className={`pb-2.5 transition-colors border-b-2 ${
                  activeTab === 'hardware'
                    ? 'border-paytm-cyan text-paytm-navy font-bold'
                    : 'border-transparent text-ink-secondary hover:text-ink-primary'
                }`}
              >
                Soundbox Hardware Proof (4G)
              </button>
              <button
                onClick={() => setActiveTab('npci')}
                className={`pb-2.5 transition-colors border-b-2 ${
                  activeTab === 'npci'
                    ? 'border-paytm-cyan text-paytm-navy font-bold'
                    : 'border-transparent text-ink-secondary hover:text-ink-primary'
                }`}
              >
                NPCI & Gateway Audit
              </button>
            </div>

            {/* Tab Body */}
            <div className="p-6 overflow-y-auto flex-1 font-sans text-xs">
              {activeTab === 'docket' && (
                <div className="space-y-4">
                  <div className="p-3 bg-surface-canvas rounded-lg border border-surface-border text-ink-secondary leading-relaxed">
                    <p className="font-semibold text-ink-primary mb-1">Customer Claim:</p>
                    <p className="italic">"{packet.customer_claim}"</p>
                  </div>

                  <div className="bg-surface-canvas p-4 rounded-lg border border-surface-border font-mono text-[11px] text-ink-primary whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
                    {packet.arbitration_docket_markdown}
                  </div>
                </div>
              )}

              {activeTab === 'hardware' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">Device Model</p>
                      <p className="font-semibold text-ink-primary">{packet.soundbox_proof.device_model}</p>
                    </div>
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">Device IMEI / Serial</p>
                      <p className="font-mono font-semibold text-ink-primary">{packet.soundbox_proof.imei}</p>
                    </div>
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">In-Store Voice Confirmation</p>
                      <p className="font-semibold text-status-resolved-text flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-status-resolved-border inline-block" />
                        {packet.soundbox_proof.broadcast_status}
                      </p>
                    </div>
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">Chime Timestamp (Counter Proof)</p>
                      <p className="font-mono text-ink-primary">{packet.soundbox_proof.audio_broadcast_time}</p>
                    </div>
                  </div>
                  <div className="p-3 bg-status-verifying-bg border border-status-verifying-border rounded-lg text-ink-primary text-xs">
                    <strong>Cell Tower Telemetry Match:</strong> Cell ID <code className="font-mono">{packet.soundbox_proof.tower_cell_id}</code> matches registered merchant GPS coordinates at transaction timestamp, disproving remote fraud.
                  </div>
                </div>
              )}

              {activeTab === 'npci' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">NPCI RRN (Retrieval Reference)</p>
                      <p className="font-mono font-bold text-paytm-navy">{packet.npci_trace.npci_rrn}</p>
                    </div>
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">Payer VPA</p>
                      <p className="font-mono text-ink-primary">{packet.npci_trace.payer_vpa}</p>
                    </div>
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">Bank Authorization Code</p>
                      <p className="font-mono text-ink-primary">{packet.npci_trace.auth_code}</p>
                    </div>
                    <div className="p-4 bg-surface-canvas rounded-lg border border-surface-border">
                      <p className="text-[11px] text-ink-muted mb-1">Gateway Ledger Verdict</p>
                      <p className="font-semibold text-status-resolved-text">{packet.npci_trace.gateway_status}</p>
                    </div>
                  </div>
                  <p className="text-ink-secondary text-xs">
                    The autonomous agent verified that only one ₹1,200 credit entered the merchant settlement account. The second debit is an unreversed hold at the customer's issuing bank.
                  </p>
                </div>
              )}
            </div>

            {/* Footer Actions */}
            <div className="px-6 py-4 border-t border-surface-border bg-surface-canvas flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="px-3 py-2 rounded-lg border border-surface-border hover:bg-surface-card text-ink-primary font-medium text-xs flex items-center gap-1.5 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  {copied ? 'Copied to Clipboard!' : 'Copy Legal Docket'}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={onClose}
                  className="px-3 py-2 rounded-lg border border-surface-border hover:bg-surface-card text-ink-secondary font-medium text-xs transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitted}
                  className={`px-4 py-2 rounded-lg font-semibold text-xs transition-all shadow-sm flex items-center gap-1.5 ${
                    isSubmitted
                      ? 'bg-status-resolved-bg text-status-resolved-text border border-status-resolved-border'
                      : 'bg-paytm-navy text-surface-card hover:bg-paytm-navy/90'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {isSubmitted ? 'Submitted to NPCI Portal' : 'Submit Dispute Defense to NPCI'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
