import { useState, useRef, useEffect, FC, KeyboardEvent } from 'react'
import { ChatMessage, DiscrepancySummary } from '../types/api'
import { EvidencePanel } from './EvidencePanel'
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
  Radio,
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
  activeConversationId,
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

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)
  const timerRef = useRef<any>(null)

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
    onSendMessage(inputText)
    setInputText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend()
  }

  // Fallback to typed input immediately upon permission denial
  const fallbackToTyped = (reason: string) => {
    setIsRecording(false)
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore
      }
    }
    setPermissionDenied(reason)
    setTimeout(() => {
      inputRef.current?.focus()
    }, 100)
  }

  // Toggle Voice Recording
  const handleMicToggle = async () => {
    // If currently recording, stop and allow preview
    if (isRecording) {
      setIsRecording(false)
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {
          // ignore
        }
      }
      return
    }

    setPermissionDenied(null)

    // 1. Request microphone permission
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        await navigator.mediaDevices.getUserMedia({ audio: true })
      }
    } catch (err: any) {
      fallbackToTyped('Microphone permission denied. Switched to typed input immediately.')
      return
    }

    // 2. Disclose AI identity and create voice session per PRD §5.2 / §9
    try {
      const token = 'demo-token-merchant-1'
      const sessRes = await fetch('http://localhost:8000/api/v1/voice/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: activeConversationId || undefined,
          language: currentLanguage,
        }),
      })
      if (sessRes.ok) {
        setAiDisclosed(true)
        if (onVoiceSessionInit) onVoiceSessionInit()
      }
    } catch {
      // In offline or mock mode, keep going
      setAiDisclosed(true)
    }

    // 3. Start Browser Speech Recognition
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition()
        recognitionRef.current = recognition
        recognition.continuous = true
        recognition.interimResults = true

        // Map language
        if (currentLanguage === 'hi') {
          recognition.lang = 'hi-IN'
        } else if (currentLanguage === 'mr') {
          recognition.lang = 'mr-IN'
        } else {
          recognition.lang = 'en-IN'
        }

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
        // Fallback to simulation if speech recognition constructor fails
        startSimulatedVoice()
      }
    } else {
      // Fallback: Web Speech API unsupported in this environment
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

  // Browser Speech Synthesis
  const handleSpeak = (msgId: string, text: string, lang: string) => {
    if (!window.speechSynthesis) return

    if (activeSpeakingMsgId === msgId) {
      window.speechSynthesis.cancel()
      setActiveSpeakingMsgId(null)
      return
    }

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)

    if (lang === 'hi') {
      utterance.lang = 'hi-IN'
    } else if (lang === 'mr') {
      utterance.lang = 'mr-IN'
    } else {
      utterance.lang = 'en-IN'
    }

    utterance.onend = () => setActiveSpeakingMsgId(null)
    utterance.onerror = () => setActiveSpeakingMsgId(null)

    setActiveSpeakingMsgId(msgId)
    window.speechSynthesis.speak(utterance)
  }

  return (
    <div className="flex flex-col h-[700px] bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
      {/* Workspace Header */}
      <div className="p-4 bg-slate-950/70 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-sky-500 to-cyan-400 flex items-center justify-center text-slate-950 shadow-md shadow-sky-500/20">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-white">OpsSaathi AI Workspace</span>
              <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Online
              </span>
              {aiDisclosed && (
                <span className="text-[10px] text-amber-400 font-semibold bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Radio className="h-3 w-3" />
                  Voice Enabled
                </span>
              )}
              {isReplayMode && (
                <span
                  className="text-[10px] text-amber-300 font-semibold bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm"
                  title="Serving deterministic cached golden scenario (PRD §12.3 Replay Mode)"
                >
                  <RotateCcw className="h-2.5 w-2.5" />
                  Replay Mode
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Disclosed AI Teammate • Autonomous resolution with verified truth
            </p>
          </div>
        </div>

        <button
          onClick={onToggleTrace}
          className="flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300 bg-sky-950/40 border border-sky-800/60 px-3 py-1.5 rounded-lg font-mono transition"
        >
          <Terminal className="h-3.5 w-3.5" />
          <span>Trace ({traceCount})</span>
        </button>
      </div>

      {/* Permission Denied Alert Banner */}
      {permissionDenied && (
        <div className="px-4 py-2.5 bg-rose-950/80 border-b border-rose-800/80 flex items-center justify-between text-xs text-rose-200 animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>{permissionDenied}</span>
          </div>
          <button
            onClick={() => setPermissionDenied(null)}
            className="text-rose-400 hover:text-rose-200 text-xs px-2 py-0.5 rounded"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
            <div className="h-12 w-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">How can OpsSaathi help today?</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
                Report missing settlements by typing or speaking in English, हिन्दी, or मराठी.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'USER'
            const isVoice = msg.channel === 'VOICE'
            const isSpeaking = activeSpeakingMsgId === msg.id

            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : ''}`}
              >
                <div
                  className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                    isUser
                      ? 'bg-sky-500 text-slate-950'
                      : 'bg-slate-800 text-sky-400 border border-slate-700'
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                <div className="space-y-2">
                  <div
                    className={`p-3.5 rounded-2xl text-xs leading-relaxed ${
                      isUser
                        ? 'bg-sky-600 text-white rounded-tr-none'
                        : 'bg-slate-800/90 text-slate-200 border border-slate-700/80 rounded-tl-none'
                    }`}
                  >
                    {/* Channel Tag */}
                    {isVoice && (
                      <div className="flex items-center gap-1 text-[10px] text-sky-200/90 mb-1 font-semibold">
                        <Mic className="h-3 w-3" />
                        <span>Voice Submission</span>
                      </div>
                    )}

                    {/* Replay Cache Badge */}
                    {msg.is_replay && (
                      <div className="flex items-center gap-1 text-[10px] text-amber-300 font-semibold bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-full w-fit mb-1 shadow-sm">
                        <RotateCcw className="h-2.5 w-2.5" />
                        <span>Replay Cache</span>
                      </div>
                    )}

                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {/* Speech Synthesis Audio Button on Assistant Message */}
                    {!isUser && (
                      <div className="mt-2 pt-2 border-t border-slate-700/60 flex items-center gap-2">
                        <button
                          onClick={() => handleSpeak(msg.id, msg.content, msg.language)}
                          className={`flex items-center gap-1 text-[11px] px-2 py-0.5 rounded transition ${
                            isSpeaking
                              ? 'bg-sky-500 text-slate-950 font-semibold'
                              : 'text-slate-400 hover:text-sky-300 hover:bg-slate-700/50'
                          }`}
                          title="Speak reply aloud (Browser Speech Synthesis)"
                        >
                          {isSpeaking ? (
                            <>
                              <VolumeX className="h-3.5 w-3.5" />
                              <span>Stop Audio</span>
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

                  {/* Evidence & Investigation Panel on assistant message if available */}
                  {!isUser && evidenceSummary && (
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
          <div className="flex gap-3 max-w-[80%]">
            <div className="h-8 w-8 rounded-lg bg-slate-800 text-sky-400 border border-slate-700 flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4 animate-spin" />
            </div>
            <div className="p-3.5 bg-slate-800/90 text-slate-400 text-xs rounded-2xl rounded-tl-none border border-slate-700/80 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-sky-400 animate-ping" />
              <span>OpsSaathi is investigating ledger & applying policy...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Live Voice Recording & Transcript Preview Card */}
      {(isRecording || transcriptPreview) && (
        <div className="m-3 p-3.5 bg-slate-950/95 border border-sky-500/40 rounded-xl shadow-2xl animate-fadeIn space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="relative flex items-center justify-center">
                <span className="absolute h-6 w-6 rounded-full bg-rose-500/30 animate-ping" />
                <span className="relative h-4 w-4 rounded-full bg-rose-500 flex items-center justify-center text-white">
                  <Mic className="h-2.5 w-2.5" />
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">
                    {isRecording ? 'Listening...' : 'Transcript Preview'}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {isRecording ? `00:${recordingSeconds < 10 ? '0' : ''}${recordingSeconds}` : ''}
                  </span>
                </div>
                <p className="text-[10px] text-amber-400 flex items-center gap-1">
                  <Radio className="h-3 w-3" />
                  AI-Identity Disclosed • OpsSaathi AI Operations Teammate
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              {isRecording && (
                <button
                  onClick={handleMicToggle}
                  className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-medium transition"
                >
                  Done Speaking
                </button>
              )}
              <button
                onClick={handleCancelVoice}
                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-white rounded-lg transition"
                title="Cancel Voice"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Transcript editable box */}
          <div className="bg-slate-900 border border-slate-700/80 rounded-lg p-2.5">
            <textarea
              value={transcriptPreview}
              onChange={(e) => setTranscriptPreview(e.target.value)}
              placeholder="Speak now or edit transcript preview here..."
              rows={2}
              className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-500 outline-none resize-none"
            />
          </div>

          {/* Preview Action Buttons */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleEditInInput}
                className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition border border-slate-700"
              >
                <Edit3 className="h-3 w-3" />
                <span>Type Instead</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCancelVoice}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg text-xs transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitVoiceTranscript}
                disabled={!transcriptPreview.trim() || isSending}
                className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-sky-500 to-cyan-500 hover:from-sky-400 hover:to-cyan-400 text-slate-950 font-bold rounded-lg text-xs transition shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Check className="h-3.5 w-3.5" />
                <span>Submit Voice</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Suggested Quick Prompts */}
      <div className="px-4 py-2 bg-slate-950/50 border-t border-slate-800/80 flex gap-2 overflow-x-auto text-xs">
        <button
          onClick={() => onSendMessage('My ₹6,000 payment from yesterday is missing from settlement')}
          className="shrink-0 bg-slate-800 hover:bg-slate-700/80 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700/60 transition"
        >
          Missing ₹6,000 from settlement
        </button>
        <button
          onClick={() => onSendMessage('Check my latest settlement batch status')}
          className="shrink-0 bg-slate-800 hover:bg-slate-700/80 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700/60 transition"
        >
          Check settlement status
        </button>
        <button
          onClick={() => onSendMessage('माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये का नाही?')}
          className="shrink-0 bg-slate-800 hover:bg-slate-700/80 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700/60 transition"
        >
          मराठी: सेटलमेंट अडकले आहे
        </button>
      </div>

      {/* Input Bar */}
      <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center gap-2">
        <button
          onClick={handleMicToggle}
          className={`p-2.5 rounded-xl border transition ${
            isRecording
              ? 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse'
              : 'bg-slate-800 text-sky-400 border-slate-700 hover:bg-slate-700'
          }`}
          title={isRecording ? 'Stop Recording' : 'Start Voice Input (Mic Permission & AI Disclosed)'}
        >
          {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>

        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            permissionDenied
              ? 'Type here (Microphone fallback active)...'
              : 'Ask OpsSaathi in English, हिन्दी, or मराठी...'
          }
          disabled={isSending}
          className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-sky-500 transition"
        />

        <button
          onClick={handleSend}
          disabled={!inputText.trim() || isSending}
          className="p-2.5 bg-sky-500 hover:bg-sky-400 text-slate-950 rounded-xl font-bold transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-sky-500/20"
          title="Send Message"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
