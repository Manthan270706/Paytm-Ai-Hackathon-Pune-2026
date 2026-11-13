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
} from 'lucide-react'

interface ChatWorkspaceProps {
  messages: ChatMessage[]
  evidenceSummary: DiscrepancySummary | null
  onSendMessage: (text: string) => void
  isSending: boolean
  onToggleTrace: () => void
  traceCount: number
  activeCaseId: string | null
}

export const ChatWorkspace: FC<ChatWorkspaceProps> = ({
  messages,
  evidenceSummary,
  onSendMessage,
  isSending,
  onToggleTrace,
  traceCount,
  activeCaseId,
}) => {
  const [inputText, setInputText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending])

  const handleSend = () => {
    if (!inputText.trim() || isSending) return
    onSendMessage(inputText)
    setInputText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend()
  }

  const handleMicToggle = () => {
    if (!isRecording) {
      setIsRecording(true)
      // Deterministic speech simulation per PRD §12
      setTimeout(() => {
        setInputText('माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही')
        setIsRecording(false)
      }, 1500)
    } else {
      setIsRecording(false)
    }
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
                Report missing settlements, inquire about fee rules, or ask to re-sync batches.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'USER'
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
                    {msg.content}
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
              ? 'bg-rose-500/20 text-rose-400 border-rose-500/30 animate-pulse'
              : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
          }`}
          title="Toggle Voice (Sarvam STT)"
        >
          {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask OpsSaathi in English, हिन्दी, or मराठी..."
          disabled={isSending}
          className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-sky-500 transition"
        />

        <button
          onClick={handleSend}
          disabled={!inputText.trim() || isSending}
          className="p-2.5 bg-sky-500 hover:bg-sky-400 text-slate-950 rounded-xl font-bold transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-sky-500/20"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
