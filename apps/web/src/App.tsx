import { useState, useEffect } from 'react'
import {
  UserRole,
  MerchantProfile,
  TransactionItem,
  SettlementBatchItem,
  SupportCaseItem,
  ChatMessage,
  TraceEvent,
  DiscrepancySummary,
  CaseDetail,
  VerificationResult,
  OutcomeMetrics,
  IntegrationHealth,
} from './types/api'
import { Header } from './components/Header'
import { MerchantDashboard } from './components/MerchantDashboard'
import { ChatWorkspace } from './components/ChatWorkspace'
import { OperationsConsole } from './components/OperationsConsole'
import { TracePanel } from './components/TracePanel'
import { IntegrationHealthModal } from './components/IntegrationHealthModal'

const API_BASE = 'http://localhost:8000/api/v1'

export default function App() {
  const [currentRole, setCurrentRole] = useState<UserRole>('MERCHANT')
  const [currentLanguage, setCurrentLanguage] = useState<string>('en')
  const [profile, setProfile] = useState<MerchantProfile | null>(null)
  const [transactions, setTransactions] = useState<TransactionItem[]>([])
  const [settlements, setSettlements] = useState<SettlementBatchItem[]>([])
  const [cases, setCases] = useState<SupportCaseItem[]>([])
  const [discrepancy, setDiscrepancy] = useState<string>('6000.00')

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [evidenceSummary, setEvidenceSummary] = useState<DiscrepancySummary | null>(null)
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [activeCaseDetail, setActiveCaseDetail] = useState<CaseDetail | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false)
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [isTraceOpen, setIsTraceOpen] = useState(false)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null)
  const [isReplayMode, setIsReplayMode] = useState<boolean>(false)
  const [metrics, setMetrics] = useState<OutcomeMetrics | null>(null)
  const [isLoadingMetrics, setIsLoadingMetrics] = useState<boolean>(false)
  const [health, setHealth] = useState<IntegrationHealth | null>(null)
  const [isLoadingHealth, setIsLoadingHealth] = useState<boolean>(false)
  const [isHealthModalOpen, setIsHealthModalOpen] = useState<boolean>(false)

  const token =
    currentRole === 'MERCHANT'
      ? 'demo-token-merchant-1'
      : 'demo-token-support_agent-1'

  const loadMetrics = async () => {
    try {
      setIsLoadingMetrics(true)
      const res = await fetch(`${API_BASE}/metrics`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMetrics(data.data)
      }
    } catch (err) {
      console.error('Failed to load metrics', err)
    } finally {
      setIsLoadingMetrics(false)
    }
  }

  const loadHealth = async () => {
    try {
      setIsLoadingHealth(true)
      const res = await fetch(`${API_BASE}/health`)
      if (res.ok) {
        const data = await res.json()
        setHealth(data.data)
        if (data.data?.demo_deterministic) {
          setIsReplayMode(true)
        }
      }
    } catch (err) {
      console.error('Failed to load health', err)
    } finally {
      setIsLoadingHealth(false)
    }
  }

  // Fetch initial dashboard and case data
  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const headers = { Authorization: `Bearer ${token}` }

      // 1. Merchant Profile
      const merchantRes = await fetch(
        `${API_BASE}/merchants/11111111-1111-1111-1111-111111111111`,
        { headers }
      )
      if (merchantRes.ok) {
        const mData = await merchantRes.json()
        setProfile(mData.data)
      }

      // 2. Transactions
      const txnRes = await fetch(`${API_BASE}/transactions`, { headers })
      if (txnRes.ok) {
        const tData = await txnRes.json()
        setTransactions(tData.data?.items || [])
      }

      // 3. Settlements
      const stlRes = await fetch(`${API_BASE}/settlements`, { headers })
      if (stlRes.ok) {
        const sData = await stlRes.json()
        setSettlements(sData.data?.batches || [])
        if (sData.data?.discrepancy_amount) {
          setDiscrepancy(sData.data.discrepancy_amount)
        }
      }

      // 4. Cases
      const caseRes = await fetch(`${API_BASE}/cases`, { headers })
      if (caseRes.ok) {
        const cData = await caseRes.json()
        const fetchedCases = cData.data?.items || []
        setCases(fetchedCases)
        if (fetchedCases.length > 0) {
          const targetId = activeCaseId && fetchedCases.some((c: any) => c.id === activeCaseId)
            ? activeCaseId
            : fetchedCases[0].id
          loadCaseDetail(targetId)
        }
      }

      // 5. Outcome Metrics & Integration Health
      loadMetrics()
      loadHealth()

      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to connect to OpsSaathi API')
    } finally {
      setLoading(false)
    }
  }

  // Fetch full case details and timeline
  const loadCaseDetail = async (caseId: string) => {
    try {
      setIsLoadingDetail(true)
      const headers = { Authorization: `Bearer ${token}` }
      const res = await fetch(`${API_BASE}/cases/${caseId}`, { headers })
      if (res.ok) {
        const dData = await res.json()
        setActiveCaseDetail(dData.data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoadingDetail(false)
    }
  }

  useEffect(() => {
    loadDashboardData()
  }, [currentRole])

  // Handle sending a message to the agent
  // Handle sending a message to the agent
  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'USER',
      content: text,
      language: currentLanguage,
      created_at: new Date().toISOString(),
      channel: 'CHAT',
    }
    setMessages((prev) => [...prev, userMsg])
    setIsSending(true)

    try {
      const res = await fetch(`${API_BASE}/agent/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: conversationId || undefined,
          message: text,
          language: currentLanguage,
        }),
      })

      if (!res.ok) throw new Error('Agent execution failed')
      const data = await res.json()
      const agentData = data.data

      const botMsg: ChatMessage = {
        id: `msg-${Date.now()}-bot`,
        role: 'ASSISTANT',
        content: agentData.reply,
        language: agentData.language,
        created_at: new Date().toISOString(),
        channel: 'CHAT',
        is_replay: agentData.is_replay,
        llm_source: agentData.llm_source,
      }
      setMessages((prev) => [...prev, botMsg])

      if (agentData.is_replay) {
        setIsReplayMode(true)
      }
      if (agentData.conversation_id) {
        setConversationId(agentData.conversation_id)
      }
      if (agentData.evidence_summary) {
        setEvidenceSummary(agentData.evidence_summary)
      }
      if (agentData.active_case_id) {
        setActiveCaseId(agentData.active_case_id)
      }

      // Stream SSE trace events for this run
      if (agentData.run_id) {
        setActiveRunId(agentData.run_id)
        startSseTrace(agentData.run_id)
      }

      // Refresh cases list
      loadDashboardData()
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        role: 'ASSISTANT',
        content: `Error contacting agent: ${err.message}`,
        language: 'en',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsSending(false)
    }
  }

  // Handle submitting voice transcript with channel continuity
  const handleSendVoice = async (transcript: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'USER',
      content: transcript,
      language: currentLanguage,
      created_at: new Date().toISOString(),
      channel: 'VOICE',
    }
    setMessages((prev) => [...prev, userMsg])
    setIsSending(true)

    try {
      const res = await fetch(`${API_BASE}/voice/transcriptions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: conversationId || undefined,
          transcript,
          language: currentLanguage,
          generate_audio: true,
        }),
      })

      if (!res.ok) throw new Error('Voice transcription processing failed')
      const data = await res.json()
      const voiceData = data.data

      const botMsg: ChatMessage = {
        id: `msg-${Date.now()}-bot`,
        role: 'ASSISTANT',
        content: voiceData.reply_text,
        language: voiceData.language,
        created_at: new Date().toISOString(),
        channel: 'VOICE',
        is_replay: voiceData.is_replay,
        llm_source: voiceData.llm_source,
      }
      setMessages((prev) => [...prev, botMsg])

      if (voiceData.is_replay) {
        setIsReplayMode(true)
      }
      if (voiceData.conversation_id) {
        setConversationId(voiceData.conversation_id)
      }
      if (voiceData.evidence_summary) {
        setEvidenceSummary(voiceData.evidence_summary)
      }
      if (voiceData.active_case_id) {
        setActiveCaseId(voiceData.active_case_id)
      }

      // Stream SSE trace events for this run
      if (voiceData.run_id) {
        setActiveRunId(voiceData.run_id)
        startSseTrace(voiceData.run_id)
      }

      // Audio playback: Sarvam synthesized audio -> Browser speech synthesis fallback
      const playBrowserSpeech = () => {
        if (typeof window !== 'undefined' && window.speechSynthesis) {
          window.speechSynthesis.cancel()
          const utterance = new SpeechSynthesisUtterance(voiceData.reply_text)
          utterance.lang =
            voiceData.language === 'hi'
              ? 'hi-IN'
              : voiceData.language === 'mr'
                ? 'mr-IN'
                : 'en-IN'
          window.speechSynthesis.speak(utterance)
        }
      }

      if (voiceData.reply_audio_url) {
        const audio = new Audio(voiceData.reply_audio_url)
        audio.play().catch(() => {
          playBrowserSpeech()
        })
      } else {
        playBrowserSpeech()
      }

      // Refresh cases list
      loadDashboardData()
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        role: 'ASSISTANT',
        content: `Error processing voice turn: ${err.message}`,
        language: 'en',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsSending(false)
    }
  }

  // Stream live SSE trace events
  const startSseTrace = (runId: string) => {
    try {
      const eventSource = new EventSource(`${API_BASE}/agent/runs/${runId}/events`)
      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          setTraceEvents((prev) => [...prev, parsed])
          if (parsed.type === 'COMPLETED') {
            eventSource.close()
          }
        } catch {
          // ignore parsing error
        }
      }
      eventSource.onerror = () => {
        eventSource.close()
      }
    } catch {
      // EventSource fallback
    }
  }

  // Demo Reset
  const handleResetDemo = async () => {
    try {
      setIsResetting(true)
      const res = await fetch(`${API_BASE}/demo/reset`, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer demo-token-support_agent-1',
        },
      })
      if (res.ok) {
        setMessages([])
        setTraceEvents([])
        setEvidenceSummary(null)
        setActiveCaseId(null)
        setConversationId(null)
        setActiveCaseDetail(null)
        setVerificationResult(null)
        setIsReplayMode(false)
        await loadDashboardData()
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsResetting(false)
    }
  }

  // Simulate bank settlement
  const handleSimulateSettlement = async () => {
    try {
      setIsSimulating(true)
      const res = await fetch(`${API_BASE}/demo/simulate-settlement`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer demo-token-support_agent-1',
        },
        body: JSON.stringify({ amount: '6000.00', batch_ref: 'BATCH_20261112_01' }),
      })
      if (res.ok) {
        await loadDashboardData()
        if (activeCaseDetail?.id) {
          await loadCaseDetail(activeCaseDetail.id)
        }
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsSimulating(false)
    }
  }

  // Approve case
  const handleApproveCase = async (
    caseId: string,
    version: number,
    actionHash: string
  ) => {
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          expected_version: version,
          action_hash:
            actionHash ||
            '44efa879046efa3a441c61673e778f5ed3cb2adec16c9d57ca0f88b6139a2e02',
        }),
      })
      if (res.ok) {
        await loadDashboardData()
        await loadCaseDetail(caseId)
      }
    } catch (err) {
      console.error(err)
    }
  }

  // Reject case
  const handleRejectCase = async (
    caseId: string,
    version: number,
    actionHash: string,
    reason: string
  ) => {
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          expected_version: version,
          action_hash:
            actionHash ||
            '44efa879046efa3a441c61673e778f5ed3cb2adec16c9d57ca0f88b6139a2e02',
          reason: reason || 'Manual inspection required',
        }),
      })
      if (res.ok) {
        await loadDashboardData()
        await loadCaseDetail(caseId)
      }
    } catch (err) {
      console.error(err)
    }
  }

  // Assign case
  const handleAssignCase = async (caseId: string, version: number, queue: string) => {
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/assign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          expected_version: version,
          queue,
        }),
      })
      if (res.ok) {
        await loadDashboardData()
        await loadCaseDetail(caseId)
      }
    } catch (err) {
      console.error(err)
    }
  }

  // Verify resolution
  const handleVerifyCase = async (caseId: string) => {
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/verify`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (res.ok) {
        const data = await res.json()
        setVerificationResult(data.data)
        await loadDashboardData()
        await loadCaseDetail(caseId)
      }
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        currentLanguage={currentLanguage}
        onLanguageChange={setCurrentLanguage}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
        isReplayMode={isReplayMode}
        onOpenHealth={() => {
          setIsHealthModalOpen(true)
          loadHealth()
        }}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
        {currentRole === 'MERCHANT' ? (
          <>
            <MerchantDashboard
              profile={profile}
              transactions={transactions}
              settlements={settlements}
              cases={cases}
              discrepancy={discrepancy}
              loading={loading}
              error={error}
              onOpenChat={(prompt) => {
                if (prompt) handleSendMessage(prompt)
              }}
            />

            <div className="pt-4 border-t border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">Autonomous Merchant Support Chat</h3>
              <ChatWorkspace
                messages={messages}
                evidenceSummary={evidenceSummary}
                onSendMessage={handleSendMessage}
                onSubmitVoice={handleSendVoice}
                isSending={isSending}
                onToggleTrace={() => setIsTraceOpen(!isTraceOpen)}
                traceCount={traceEvents.length}
                activeCaseId={activeCaseId}
                currentLanguage={currentLanguage}
                activeConversationId={conversationId}
                isReplayMode={isReplayMode}
              />
            </div>
          </>
        ) : (
          <OperationsConsole
            cases={cases}
            onApproveCase={handleApproveCase}
            onRejectCase={handleRejectCase}
            onAssignCase={handleAssignCase}
            onSimulateSettlement={handleSimulateSettlement}
            onVerifyCase={handleVerifyCase}
            isSimulating={isSimulating}
            verificationResult={verificationResult}
            activeCaseDetail={activeCaseDetail}
            onSelectCase={(id) => {
              setActiveCaseId(id)
              loadCaseDetail(id)
            }}
            isLoadingDetail={isLoadingDetail}
            metrics={metrics}
            onRefreshMetrics={loadMetrics}
            isLoadingMetrics={isLoadingMetrics}
          />
        )}
      </main>

      <TracePanel
        events={traceEvents}
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
        runId={activeRunId}
      />

      <IntegrationHealthModal
        isOpen={isHealthModalOpen}
        onClose={() => setIsHealthModalOpen(false)}
        health={health}
        isLoading={isLoadingHealth}
      />
    </div>
  )
}
