import { useState, useEffect, useRef } from 'react'
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
import { API_BASE } from './config'

export interface ActionFeedback {
  type: 'error' | 'warning' | 'info' | 'success'
  title: string
  message: string
}

export default function App() {
  const [currentRole, setCurrentRole] = useState<UserRole>('MERCHANT')
  const [currentLanguage, setCurrentLanguage] = useState<string>('en')
  const [profile, setProfile] = useState<MerchantProfile | null>(null)
  const [transactions, setTransactions] = useState<TransactionItem[]>([])
  const [settlements, setSettlements] = useState<SettlementBatchItem[]>([])
  const [cases, setCases] = useState<SupportCaseItem[]>([])
  const [discrepancy, setDiscrepancy] = useState<string>('0.00')

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem('opssaathi_chat_messages')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [evidenceSummary, setEvidenceSummary] = useState<DiscrepancySummary | null>(() => {
    try {
      const saved = localStorage.getItem('opssaathi_evidence_summary')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(() => {
    try {
      return localStorage.getItem('opssaathi_conversation_id')
    } catch {
      return null
    }
  })
  const [activeCaseDetail, setActiveCaseDetail] = useState<CaseDetail | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false)
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [isTraceOpen, setIsTraceOpen] = useState(false)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const isSendingRef = useRef(false)
  const [isResetting, setIsResetting] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null)
  const [isReplayMode, setIsReplayMode] = useState<boolean>(false)
  const [metrics, setMetrics] = useState<OutcomeMetrics | null>(null)
  const [isLoadingMetrics, setIsLoadingMetrics] = useState<boolean>(false)
  const [health, setHealth] = useState<IntegrationHealth | null>(null)
  const [isLoadingHealth, setIsLoadingHealth] = useState<boolean>(false)
  const [isHealthModalOpen, setIsHealthModalOpen] = useState<boolean>(false)
  const [actionFeedback, setActionFeedback] = useState<ActionFeedback | null>(null)

  // Synchronize chat state to localStorage to survive page refreshes
  useEffect(() => {
    try {
      if (messages.length > 0) {
        localStorage.setItem('opssaathi_chat_messages', JSON.stringify(messages))
      } else {
        localStorage.removeItem('opssaathi_chat_messages')
      }
    } catch {
      // ignore
    }
  }, [messages])

  useEffect(() => {
    try {
      if (conversationId) {
        localStorage.setItem('opssaathi_conversation_id', conversationId)
      } else {
        localStorage.removeItem('opssaathi_conversation_id')
      }
    } catch {
      // ignore
    }
  }, [conversationId])

  useEffect(() => {
    try {
      localStorage.removeItem('opssaathi_active_case_id')
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    try {
      if (evidenceSummary) {
        localStorage.setItem('opssaathi_evidence_summary', JSON.stringify(evidenceSummary))
      } else {
        localStorage.removeItem('opssaathi_evidence_summary')
      }
    } catch {
      // ignore
    }
  }, [evidenceSummary])

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
        if (sData.data?.discrepancy_amount !== undefined && sData.data?.discrepancy_amount !== null) {
          setDiscrepancy(String(sData.data.discrepancy_amount))
        }
      }

      // 4. Cases
      const caseRes = await fetch(`${API_BASE}/cases`, { headers })
      if (caseRes.ok) {
        const cData = await caseRes.json()
        const fetchedCases = cData.data?.items || []
        setCases(fetchedCases)
        if (activeCaseId && fetchedCases.some((c: any) => c.id === activeCaseId)) {
          loadCaseDetail(activeCaseId)
        } else {
          setActiveCaseDetail(null)
        }
      }

      // 5. Outcome Metrics & Integration Health
      loadMetrics()
      loadHealth()

      // 6. Active Conversation Messages (fallback if local storage was empty)
      try {
        const msgRes = await fetch(`${API_BASE}/agent/conversations/active/messages`, { headers })
        if (msgRes.ok) {
          const mData = await msgRes.json()
          if (mData.data?.messages && mData.data.messages.length > 0) {
            setMessages((current) => (current.length === 0 ? mData.data.messages : current))
            if (mData.data.conversation_id) {
              setConversationId((curr) => curr || mData.data.conversation_id)
            }
          }
        }
      } catch {
        // ignore
      }

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
  const handleSendMessage = async (text: string) => {
    if (!text || !text.trim() || isSendingRef.current) return
    isSendingRef.current = true
    setIsSending(true)

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'USER',
      content: text,
      language: currentLanguage,
      created_at: new Date().toISOString(),
      channel: 'CHAT',
    }
    setMessages((prev) => [...prev, userMsg])

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

      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.error?.message || `Agent execution failed (${res.status})`)
      }
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
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last && last.role === 'ASSISTANT' && last.content === botMsg.content) {
          return prev
        }
        return [...prev, botMsg]
      })

      if (agentData.is_replay) {
        setIsReplayMode(true)
      }
      if (agentData.conversation_id) {
        setConversationId(agentData.conversation_id)
      }
      setEvidenceSummary(agentData.evidence_summary || null)
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
      isSendingRef.current = false
      setIsSending(false)
    }
  }

  // Handle submitting voice transcript with channel continuity
  const handleSendVoice = async (transcript: string) => {
    if (!transcript || !transcript.trim() || isSendingRef.current) return
    isSendingRef.current = true
    setIsSending(true)

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'USER',
      content: transcript,
      language: currentLanguage,
      created_at: new Date().toISOString(),
      channel: 'VOICE',
    }
    setMessages((prev) => [...prev, userMsg])

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

      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.error?.message || `Voice transcription processing failed (${res.status})`)
      }
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
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last && last.role === 'ASSISTANT' && last.content === botMsg.content) {
          return prev
        }
        return [...prev, botMsg]
      })

      if (voiceData.is_replay) {
        setIsReplayMode(true)
      }
      if (voiceData.conversation_id) {
        setConversationId(voiceData.conversation_id)
      }
      setEvidenceSummary(voiceData.evidence_summary || null)
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
      isSendingRef.current = false
      setIsSending(false)
    }
  }

  // Stream live SSE trace events
  const startSseTrace = async (runId: string) => {
    try {
      const res = await fetch(`${API_BASE}/agent/runs/${runId}/events`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok || !res.body) return
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let isDone = false
      while (!isDone) {
        const result = await reader.read()
        isDone = result.done
        if (isDone || !result.value) break
        buffer += decoder.decode(result.value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''
        for (const chunk of chunks) {
          const lines = chunk.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const parsed = JSON.parse(line.slice(6))
                setTraceEvents((prev) => [...prev, parsed])
              } catch {
                // ignore parsing error
              }
            }
          }
        }
      }
    } catch {
      // Stream fallback
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
        try {
          localStorage.removeItem('opssaathi_chat_messages')
          localStorage.removeItem('opssaathi_conversation_id')
          localStorage.removeItem('opssaathi_active_case_id')
          localStorage.removeItem('opssaathi_evidence_summary')
        } catch {
          // ignore
        }
        setMessages([])
        setTraceEvents([])
        setEvidenceSummary(null)
        setActiveCaseId(null)
        setConversationId(null)
        setActiveCaseDetail(null)
        setVerificationResult(null)
        setIsReplayMode(false)
        setActionFeedback({
          type: 'info',
          title: 'Demo Environment Reset',
          message: 'Frozen baseline restored: ₹6,000.00 discrepancy, support cases reset.',
        })
        await loadDashboardData()
      } else {
        const errData = await res.json().catch(() => null)
        setActionFeedback({
          type: 'error',
          title: 'Reset Failed',
          message: errData?.error?.message || `Demo reset failed (${res.status})`,
        })
      }
    } catch (err: any) {
      console.error(err)
      setActionFeedback({
        type: 'error',
        title: 'Connection Error',
        message: err.message || 'Failed to connect to reset endpoint',
      })
    } finally {
      setIsResetting(false)
    }
  }

  // Simulate bank settlement
  const handleSimulateSettlement = async () => {
    try {
      setIsSimulating(true)
      const targetBatch = settlements.length > 0 ? settlements[0].batch_ref : 'BATCH_20261112_01'
      const targetAmount = parseFloat(discrepancy || '0') > 0 ? discrepancy : '6000.00'
      const res = await fetch(`${API_BASE}/demo/simulate-settlement`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer demo-token-support_agent-1',
        },
        body: JSON.stringify({ amount: targetAmount, batch_ref: targetBatch }),
      })
      if (res.ok) {
        setActionFeedback({
          type: 'success',
          title: 'Bank Credit Simulated',
          message: `₹${parseFloat(targetAmount).toLocaleString('en-IN', { minimumFractionDigits: 2 })} credit recorded on ledger. Click "Run Independent Verification" to verify and close this case.`,
        })
        await loadDashboardData()
        if (activeCaseDetail?.id) {
          await loadCaseDetail(activeCaseDetail.id)
        }
      } else {
        const errData = await res.json().catch(() => null)
        const errMsg = errData?.error?.message || `Simulation failed (${res.status})`
        setActionFeedback({
          type: 'error',
          title: 'Simulation Failed',
          message: errMsg,
        })
        throw new Error(errMsg)
      }
    } catch (err: any) {
      console.error(err)
      throw err
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
        setActionFeedback({
          type: 'success',
          title: 'Settlement Re-Sync Approved',
          message: 'Case is now in VERIFYING status. Step 2: Click "Simulate Bank Settlement" to deposit credit, then run verification.',
        })
        await loadDashboardData()
        await loadCaseDetail(caseId)
      } else {
        const errData = await res.json().catch(() => null)
        const errMsg = errData?.error?.message || `Approval failed with status ${res.status}`
        setActionFeedback({
          type: 'error',
          title: 'Approval Failed',
          message: errMsg,
        })
        throw new Error(errMsg)
      }
    } catch (err: any) {
      console.error(err)
      throw err
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
        setActionFeedback({
          type: 'info',
          title: 'Action Rejected',
          message: 'Settlement re-sync rejected with documented reason.',
        })
        await loadDashboardData()
        await loadCaseDetail(caseId)
      } else {
        const errData = await res.json().catch(() => null)
        const errMsg = errData?.error?.message || `Rejection failed (${res.status})`
        setActionFeedback({
          type: 'error',
          title: 'Rejection Failed',
          message: errMsg,
        })
        throw new Error(errMsg)
      }
    } catch (err: any) {
      console.error(err)
      throw err
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
        setActionFeedback({
          type: 'info',
          title: 'Queue Updated',
          message: `Case successfully assigned to ${queue}.`,
        })
        await loadDashboardData()
        await loadCaseDetail(caseId)
      } else {
        const errData = await res.json().catch(() => null)
        const errMsg = errData?.error?.message || `Assignment failed (${res.status})`
        setActionFeedback({
          type: 'error',
          title: 'Assignment Failed',
          message: errMsg,
        })
        throw new Error(errMsg)
      }
    } catch (err: any) {
      console.error(err)
      throw err
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
        if (data.data.verification_result === 'PASS') {
          setActionFeedback({
            type: 'success',
            title: 'Verification Passed',
            message: 'Ledger verified: ₹0.00 discrepancy. Case has been RESOLVED.',
          })
        } else {
          const discRemains =
            data.data?.expected_net && data.data?.after_observed
              ? (parseFloat(data.data.expected_net) - parseFloat(data.data.after_observed)).toFixed(2)
              : '6,000.00'
          setActionFeedback({
            type: 'warning',
            title: 'Verification Discrepancy Remains',
            message: `Discrepancy of ₹${discRemains} detected. Bank settlement credit has not been processed yet. Click "Simulate Bank Settlement" to deposit credit, then re-verify.`,
          })
        }
        await loadDashboardData()
        await loadCaseDetail(caseId)
      } else {
        const errData = await res.json().catch(() => null)
        const errMsg = errData?.error?.message || `Verification failed (${res.status})`
        setActionFeedback({
          type: 'error',
          title: 'Verification Pre-condition Not Met',
          message: errMsg.includes('VERIFYING')
            ? 'This case must be approved by supervisor before it can be verified. Please review and authorize the re-sync in Step 1 first.'
            : errMsg,
        })
        throw new Error(errMsg)
      }
    } catch (err: any) {
      console.error(err)
      throw err
    }
  }

  // Create support case
  const handleCreateCase = async (data: {
    category: string
    priority: string
    queue: string
    summary: string
  }) => {
    try {
      const idempotencyKey = `create-case-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
      const res = await fetch(`${API_BASE}/cases`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify({
          category: data.category,
          priority: data.priority,
          queue: data.queue,
          summary: data.summary,
        }),
      })
      if (res.ok) {
        const result = await res.json()
        const createdCase = result?.data
        setActionFeedback({
          type: 'success',
          title: 'Case Created',
          message: `Case ${createdCase?.case_number || 'new'} successfully created in ${data.queue} queue.`,
        })
        await loadDashboardData()
        if (createdCase?.id) {
          setActiveCaseId(createdCase.id)
          await loadCaseDetail(createdCase.id)
        }
      } else {
        const errData = await res.json().catch(() => null)
        const errMsg = errData?.error?.message || `Failed to create case (${res.status})`
        setActionFeedback({
          type: 'error',
          title: 'Case Creation Failed',
          message: errMsg,
        })
        throw new Error(errMsg)
      }
    } catch (err: any) {
      console.error(err)
      throw err
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
              if (!id) {
                setActiveCaseId(null)
                setActiveCaseDetail(null)
              } else {
                setActiveCaseId(id)
                loadCaseDetail(id)
              }
            }}
            isLoadingDetail={isLoadingDetail}
            metrics={metrics}
            onRefreshMetrics={loadMetrics}
            isLoadingMetrics={isLoadingMetrics}
            actionFeedback={actionFeedback}
            onClearFeedback={() => setActionFeedback(null)}
            onCreateCase={handleCreateCase}
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
