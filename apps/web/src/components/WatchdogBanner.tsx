import React, { useState } from 'react'
import { WatchdogAlert } from '../types/api'

interface WatchdogBannerProps {
  alert: WatchdogAlert | null
  currentLanguage: string
  onScanNow?: () => Promise<void>
  onViewCase?: (caseId: string) => void
}

export const WatchdogBanner: React.FC<WatchdogBannerProps> = ({
  alert,
  currentLanguage,
  onScanNow,
  onViewCase,
}) => {
  const [isPlayingSoundbox, setIsPlayingSoundbox] = useState(false)
  const [isScanning, setIsScanning] = useState(false)

  if (!alert) return null

  const localizedMsg =
    alert.messages[currentLanguage] ||
    alert.messages['en'] ||
    alert.delay_reason

  const handlePlaySoundbox = () => {
    setIsPlayingSoundbox(true)
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      const textToSpeak = alert.soundbox_announcement || alert.messages['hi'] || alert.messages['en']
      const utterance = new SpeechSynthesisUtterance(textToSpeak)
      utterance.lang = currentLanguage === 'hi' ? 'hi-IN' : currentLanguage === 'mr' ? 'mr-IN' : 'en-IN'
      utterance.rate = 0.95
      utterance.onend = () => setIsPlayingSoundbox(false)
      utterance.onerror = () => setIsPlayingSoundbox(false)
      window.speechSynthesis.speak(utterance)
    } else {
      setTimeout(() => setIsPlayingSoundbox(false), 2500)
    }
  }

  const handleTriggerScan = async () => {
    if (!onScanNow) return
    setIsScanning(true)
    try {
      await onScanNow()
    } finally {
      setIsScanning(false)
    }
  }

  return (
    <div
      data-testid="watchdog-banner"
      className="bg-surface-card border-2 border-paytm-cyan/40 rounded-xl p-4 shadow-sm mb-4 relative overflow-hidden transition-all"
    >
      {/* Top Banner Header */}
      <div className="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-paytm-cyan opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-paytm-cyan"></span>
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-paytm-navy">
            Paytm Pi · Proactive Settlement Watchdog
          </span>
          <span className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-semibold rounded bg-status-verifying-bg text-status-verifying-text border border-status-verifying-border">
            PROACTIVE RESOLUTION
          </span>
        </div>

        <button
          onClick={handleTriggerScan}
          disabled={isScanning}
          className="text-xs text-paytm-navy hover:text-paytm-cyan font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
          title="Manually trigger a real-time watchdog scan across nodal accounts"
        >
          <svg className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isScanning ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
        <div className="md:col-span-3">
          <p className="text-sm font-medium text-ink-primary leading-snug mb-2">
            {localizedMsg}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink-secondary">
            <span className="bg-surface-canvas px-2 py-0.5 rounded border border-surface-border font-mono">
              UTR: {alert.utr_number}
            </span>
            <span className="bg-surface-canvas px-2 py-0.5 rounded border border-surface-border">
              Expected Credit: <strong className="text-ink-primary">{alert.expected_credit_window}</strong>
            </span>
            <button
              onClick={() => onViewCase && onViewCase(alert.case_id)}
              className="text-paytm-navy font-semibold hover:underline"
            >
              #{alert.case_number}
            </button>
          </div>
        </div>

        {/* Soundbox Broadcast CTA */}
        <div className="flex md:flex-col items-center justify-end gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-surface-border">
          <button
            onClick={handlePlaySoundbox}
            className={`w-full sm:w-auto px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-sm ${
              isPlayingSoundbox
                ? 'bg-status-resolved-bg text-status-resolved-text border border-status-resolved-border animate-pulse'
                : 'bg-paytm-navy text-surface-card hover:bg-paytm-navy/90'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
            {isPlayingSoundbox ? 'Broadcasting on Soundbox...' : 'Listen on Soundbox'}
          </button>
          <span className="text-[10px] text-ink-muted text-center">
            Simulated Voice Alert
          </span>
        </div>
      </div>
    </div>
  )
}
