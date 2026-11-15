import { useState, useRef, useEffect, FC, KeyboardEvent } from 'react'
import { ChatMessage, DiscrepancySummary } from '../types/api'
import { EvidencePanel } from './EvidencePanel'
import { Button } from './Button'
import { API_BASE } from '../config'
import {
  Send,
  Mic,
  MicOff,
  Sparkles,
  Terminal,
  Bot,
  User,
  Volume2,
  VolumeX,
  Loader2,
  AlertCircle,
  Check,
  X,
  Edit3,
  RotateCcw,
} from 'lucide-react'

interface ChatWorkspaceProps {
  messages: ChatMessage[]
  evidenceSummary: DiscrepancySummary | null
  onSendMessage: (text: string) => void
  onSubmitVoice: (transcript: string) => void
  isSending: boolean
  onToggleTrace: () => void
  traceCount: number
  activeCaseId: string | null
  currentLanguage: string
  activeConversationId: string | null
  onVoiceSessionInit?: () => void
  isReplayMode?: boolean
}

export const ChatWorkspace: FC<ChatWorkspaceProps> = ({
  messages,
  evidenceSummary,
  onSendMessage,
  onSubmitVoice,
  isSending,
  onToggleTrace,
  traceCount,
  activeCaseId,
  currentLanguage,
  activeConversationId: _activeConversationId,
  onVoiceSessionInit,
  isReplayMode = false,
}) => {
  const [inputText, setInputText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [transcriptPreview, setTranscriptPreview] = useState('')
  const [permissionDenied, setPermissionDenied] = useState<string | null>(null)
  const [aiDisclosed, setAiDisclosed] = useState(false)
  const [activeSpeakingMsgId, setActiveSpeakingMsgId] = useState<string | null>(null)
  const [isSynthesizingMsgId, setIsSynthesizingMsgId] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)
  const timerRef = useRef<any>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending, transcriptPreview])

  // Timer for recording duration
  useEffect(() => {
    if (isRecording) {
      setRecordingSeconds(0)
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
      setRecordingSeconds(0)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isRecording])

  const handleSend = () => {
    if (!inputText.trim() || isSending) return
    onSendMessage(inputText.trim())
    setInputText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Voice Interaction via Web Speech API with simulated fallback
  const handleMicToggle = async () => {
    if (isRecording) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {
          // ignore
        }
      }
      setIsRecording(false)
      return
    }

    if (!aiDisclosed) {
      setAiDisclosed(true)
    }

    if (onVoiceSessionInit) {
      onVoiceSessionInit()
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    const fallbackToTyped = (reason: string) => {
      setPermissionDenied(reason)
      setIsRecording(false)
      setTimeout(() => {
        inputRef.current?.focus()
      }, 100)
    }

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition()
        recognitionRef.current = recognition
        recognition.continuous = true
        recognition.interimResults = true

        recognition.lang =
          currentLanguage === 'hi'
            ? 'hi-IN'
            : currentLanguage === 'mr'
              ? 'mr-IN'
              : 'en-IN'

        recognition.onresult = (event: any) => {
          let interimTranscript = ''
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            interimTranscript += event.results[i][0].transcript
          }
          if (interimTranscript.trim()) {
            setTranscriptPreview(interimTranscript.trim())
          }
        }

        recognition.onerror = (event: any) => {
          if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            fallbackToTyped('Microphone access blocked. Switched to typed input.')
          }
        }

        recognition.start()
        setIsRecording(true)
      } catch {
        startSimulatedVoice()
      }
    } else {
      startSimulatedVoice()
    }
  }

  const startSimulatedVoice = () => {
    setIsRecording(true)
    const preset =
      currentLanguage === 'hi'
        ? 'मेरा ₹६,००० का भुगतान सेटलमेंट में नहीं आया है'
        : currentLanguage === 'mr'
          ? 'माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही'
          : 'My ₹6,000 payment from yesterday is missing from settlement'
    setTranscriptPreview(preset)
  }

  const handleSubmitVoiceTranscript = () => {
    if (!transcriptPreview.trim() || isSending) return
    setIsRecording(false)
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore
      }
    }
    onSubmitVoice(transcriptPreview.trim())
    setTranscriptPreview('')
  }

  const handleEditInInput = () => {
    setInputText(transcriptPreview)
    setTranscriptPreview('')
    setIsRecording(false)
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore
      }
    }
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const handleCancelVoice = () => {
    setIsRecording(false)
    setTranscriptPreview('')
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore
      }
    }
  }

  // Speech Synthesis Audio Playback (Sarvam AI Neural TTS + Browser Fallback)
  const handleSpeak = async (msgId: string, text: string, lang?: string) => {
    if (activeSpeakingMsgId === msgId) {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.currentTime = 0
        audioRef.current = null
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
      setActiveSpeakingMsgId(null)
      setIsSynthesizingMsgId(null)
      return
    }

    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }

    let effectiveLang = (lang || currentLanguage || 'en').toLowerCase()
    if (/[\u0900-\u097F]/.test(text)) {
      if (
        effectiveLang === 'mr' ||
        text.includes('आहे') ||
        text.includes('नाही') ||
        text.includes('तफावत') ||
        text.includes('बॅच') ||
        text.includes('झाले')
      ) {
        effectiveLang = 'mr'
      } else if (effectiveLang === 'en') {
        effectiveLang = 'hi'
      }
    }

    setIsSynthesizingMsgId(msgId)
    try {
      const token = 'demo-token-merchant-1'
      const res = await fetch(`${API_BASE}/voice/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          text,
          language: effectiveLang,
        }),
      })

      if (res.ok) {
        const payload = await res.json()
        const b64 = payload?.data?.audio_base64
        if (b64) {
          setIsSynthesizingMsgId(null)
          setActiveSpeakingMsgId(msgId)
          const audio = new Audio(`data:audio/wav;base64,${b64}`)
          audioRef.current = audio
          audio.onended = () => {
            setActiveSpeakingMsgId(null)
            audioRef.current = null
          }
          audio.onerror = () => {
            playBrowserSpeech(text, effectiveLang, msgId)
          }
          audio.play().catch(() => {
            playBrowserSpeech(text, effectiveLang, msgId)
          })
          return
        }
      }
      playBrowserSpeech(text, effectiveLang, msgId)
    } catch {
      playBrowserSpeech(text, effectiveLang, msgId)
    }
  }

  const playBrowserSpeech = (text: string, lang: string, msgId: string) => {
    setIsSynthesizingMsgId(null)
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      setActiveSpeakingMsgId(msgId)
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = lang === 'hi' ? 'hi-IN' : lang === 'mr' ? 'mr-IN' : 'en-IN'
      utterance.onend = () => setActiveSpeakingMsgId(null)
      utterance.onerror = () => setActiveSpeakingMsgId(null)
      window.speechSynthesis.speak(utterance)
    }
  }

  return (
    <div className="bg-surface-card rounded-card border border-surface-border shadow-sm flex flex-col font-sans text-ink-primary overflow-hidden h-[540px]">
      {/* Header */}
      <div className="p-3.5 bg-surface-card border-b border-surface-divider flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-paytm-navy text-white flex items-center justify-center font-bold text-xs shadow-xs">
            <Bot className="w-4 h-4 text-paytm-cyan" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-sm text-paytm-navy">OpsSaathi AI</h3>
              <span className="text-[10px] font-semibold uppercase bg-status-completed-bg text-status-completed-text border border-status-completed-border px-1.5 py-0.2 rounded-full">
                Active
              </span>
              {isReplayMode && (
                <span className="text-[10px] font-medium bg-status-approval-bg text-status-approval-text border border-status-approval-border px-1.5 py-0.2 rounded-full flex items-center gap-1">
                  <RotateCcw className="w-2.5 h-2.5" />
                  Replay
                </span>
              )}
            </div>
            <p className="text-[11px] text-ink-muted">
              Autonomous settlement diagnosis • Vernacular voice
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onToggleTrace}
          className="flex items-center gap-1.5 text-xs text-paytm-navy hover:bg-paytm-cyan-light border border-paytm-cyan/30 px-3 py-1.5 rounded-lg font-medium transition"
        >
          <Terminal className="h-3.5 w-3.5" />
          <span>Trace ({traceCount})</span>
        </button>
      </div>

      {/* Permission Denied Alert */}
      {permissionDenied && (
        <div className="px-4 py-2 bg-status-rejected-bg border-b border-status-rejected-border flex items-center justify-between text-xs text-status-rejected-text">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{permissionDenied}</span>
          </div>
          <button
            type="button"
            onClick={() => setPermissionDenied(null)}
            className="text-xs font-semibold underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface-canvas">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
            <div className="h-12 w-12 rounded-full bg-paytm-cyan-light border border-paytm-cyan/30 flex items-center justify-center text-paytm-navy">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-paytm-navy">
                How can OpsSaathi help today?
              </h3>
              <p className="text-xs text-ink-secondary mt-1 max-w-sm">
                Ask about missing settlements, payout delays, or fee calculations in English, हिन्दी, or मराठी.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.role === 'USER'
            const isVoice = msg.channel === 'VOICE'
            const isSpeaking = activeSpeakingMsgId === msg.id
            const isSynthesizing = isSynthesizingMsgId === msg.id
            const isLatestAssistant =
              !isUser && idx === messages.map((m) => m.role).lastIndexOf('ASSISTANT')

            return (
              <div
                key={msg.id}
                className={`flex gap-2.5 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : ''}`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                    isUser
                      ? 'bg-paytm-navy text-white'
                      : 'bg-surface-card border border-surface-border text-paytm-navy'
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5 text-paytm-cyan" />}
                </div>

                <div className="space-y-2">
                  <div
                    className={`p-3 rounded-xl text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? 'bg-paytm-navy text-white rounded-tr-none shadow-xs'
                        : 'bg-surface-card text-ink-primary border border-surface-border rounded-tl-none shadow-xs'
                    }`}
                  >
                    {isVoice && (
                      <div className="flex items-center gap-1 text-[10px] text-paytm-cyan font-semibold mb-1">
                        <Mic className="h-3 w-3" />
                        <span>Voice Turn</span>
                      </div>
                    )}

                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {!isUser && (
                      <div className="mt-2 pt-2 border-t border-surface-divider flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleSpeak(msg.id, msg.content, msg.language)}
                          className={`flex items-center gap-1 text-[11px] px-2 py-0.5 rounded transition ${
                            isSpeaking
                              ? 'bg-paytm-navy text-white font-semibold'
                              : isSynthesizing
                              ? 'bg-paytm-cyan-light text-paytm-navy font-medium'
                              : 'text-ink-secondary hover:text-paytm-navy hover:bg-surface-subtle'
                          }`}
                          disabled={isSynthesizing}
                        >
                          {isSpeaking ? (
                            <>
                              <VolumeX className="h-3.5 w-3.5" />
                              <span>Stop Voice</span>
                            </>
                          ) : isSynthesizing ? (
                            <>
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              <span>Loading Audio...</span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="h-3.5 w-3.5" />
                              <span>Listen</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Evidence Card on Latest Assistant Message */}
                  {isLatestAssistant && evidenceSummary && (
                    <div className="pt-1">
                      <EvidencePanel
                        evidence={evidenceSummary}
                        activeCaseId={activeCaseId}
                        onOpenTrace={onToggleTrace}
                      />
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}

        {isSending && (
          <div className="flex gap-2.5 max-w-[80%]">
            <div className="w-7 h-7 rounded-full bg-surface-card border border-surface-border text-paytm-navy flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 animate-spin text-paytm-cyan" />
            </div>
            <div className="p-3 bg-surface-card border border-surface-border rounded-xl rounded-tl-none text-xs text-ink-secondary flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-paytm-navy" />
              <span>Verifying ledger transactions...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Voice Review Drawer */}
      {isRecording && (
        <div className="p-3 bg-surface-subtle border-t border-surface-border space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-status-rejected-text font-semibold">
              <span className="w-2 h-2 rounded-full bg-status-rejected-text animate-ping" />
              Listening ({recordingSeconds}s)...
            </span>
            <button
              type="button"
              onClick={handleEditInInput}
              className="text-paytm-navy hover:underline flex items-center gap-1 text-[11px]"
            >
              <Edit3 className="w-3 h-3" />
              <span>Edit as text</span>
            </button>
          </div>
          <div className="p-2 bg-surface-card rounded-lg border border-surface-border text-xs text-ink-primary font-medium min-h-12 flex items-center">
            {transcriptPreview || 'Listening for speech in ' + currentLanguage + '...'}
          </div>
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleCancelVoice}
              className="px-3 py-1.5 rounded-lg text-xs text-ink-secondary hover:bg-surface-subtle min-h-10"
            >
              <X className="w-3.5 h-3.5 inline mr-1" />
              Cancel
            </button>
            <Button
              variant="primary"
              onClick={handleSubmitVoiceTranscript}
              disabled={!transcriptPreview.trim() || isSending}
              className="text-xs min-h-10 px-3"
            >
              <Check className="w-3.5 h-3.5 inline mr-1" />
              Submit
            </Button>
          </div>
        </div>
      )}

      {/* Suggested Quick Prompts */}
      <div className="px-3 py-2 bg-surface-card border-t border-surface-divider flex gap-2 overflow-x-auto text-xs">
        <button
          type="button"
          onClick={() => onSendMessage('Why is ₹6,000.00 missing from my settlement on 12 Nov?')}
          disabled={isSending}
          className="shrink-0 bg-surface-subtle hover:bg-paytm-cyan-light text-paytm-navy border border-surface-border hover:border-paytm-cyan/40 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
        >
          Missing ₹6,000 from settlement
        </button>
        <button
          type="button"
          onClick={() => onSendMessage('Customer debited twice for ₹1,200 refund on Order ORD_20261111_09')}
          disabled={isSending}
          className="shrink-0 bg-surface-subtle hover:bg-surface-border text-ink-secondary px-3 py-1.5 rounded-lg text-xs font-medium transition"
        >
          Double debit refund (₹1,200)
        </button>
        <button
          type="button"
          onClick={() => onSendMessage('Paytm Soundbox did not announce ₹450 payment')}
          disabled={isSending}
          className="shrink-0 bg-surface-subtle hover:bg-surface-border text-ink-secondary px-3 py-1.5 rounded-lg text-xs font-medium transition"
        >
          Soundbox audio issue
        </button>
        <button
          type="button"
          onClick={() => onSendMessage('माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये का नाही?')}
          disabled={isSending}
          className="shrink-0 bg-surface-subtle hover:bg-surface-border text-ink-secondary px-3 py-1.5 rounded-lg text-xs font-medium transition"
        >
          मराठी: सेटलमेंट अडकले आहे
        </button>
        <button
          type="button"
          onClick={() => onSendMessage('कल का ₹6,000 सेटलमेंट बैंक खाते में अभी तक नहीं आया')}
          disabled={isSending}
          className="shrink-0 bg-surface-subtle hover:bg-surface-border text-ink-secondary px-3 py-1.5 rounded-lg text-xs font-medium transition"
        >
          हिन्दी: सेटलमेंट जांचें
        </button>
      </div>

      {/* Input Bar */}
      <div className="p-3 bg-surface-card border-t border-surface-border flex items-center gap-2">
        <button
          type="button"
          onClick={handleMicToggle}
          className={`min-h-12 min-w-12 rounded-xl flex items-center justify-center border transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${
            isRecording
              ? 'bg-status-rejected-bg text-status-rejected-text border-status-rejected-border animate-pulse'
              : 'bg-surface-subtle text-paytm-navy border-surface-border hover:bg-paytm-cyan-light'
          }`}
          title={isRecording ? 'Stop Recording' : 'Start Voice Turn'}
        >
          {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>

        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask OpsSaathi in English, हिन्दी, or मराठी..."
          disabled={isSending}
          className="flex-1 min-h-12 bg-surface-subtle border border-surface-border rounded-xl px-4 text-sm text-ink-primary placeholder:text-ink-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan transition"
        />

        <button
          type="button"
          onClick={handleSend}
          disabled={!inputText.trim() || isSending}
          className="min-h-12 min-w-12 rounded-xl bg-paytm-navy hover:bg-paytm-navy-hover text-white flex items-center justify-center font-bold transition disabled:opacity-50 disabled:cursor-not-allowed shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan"
          title="Send"
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
