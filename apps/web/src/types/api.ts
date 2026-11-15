export type SourceType = 'PAYTM_STAGING' | 'SYNTHETIC_DEMO' | 'MOCK' | 'MOCK_SETTLEMENT_OPS' | 'INTEGRATION_UNAVAILABLE'

export type UserRole = 'MERCHANT' | 'SUPPORT_AGENT' | 'SUPERVISOR'

export interface ApiResponse<T> {
  ok: boolean
  data: T
  meta?: {
    request_id: string
    source_type: SourceType
    timestamp: string
  }
  error?: {
    code: string
    message: string
    details?: any
  }
}

export interface MerchantProfile {
  id: string
  external_mid: string | null
  display_name: string
  masked_phone: string
  status: string
  source_type: SourceType
}

export interface TransactionItem {
  id: string
  provider: string
  provider_txn_id: string
  order_id: string
  amount: string
  currency: string
  status: string
  txn_time: string
  source_type: SourceType
}

export interface SettlementBatchItem {
  id: string
  batch_ref: string
  date: string
  expected_settlement_date: string
  gross: string
  fees: string
  refunds: string
  net: string
  status: string
  source_type: SourceType
}

export interface SupportCaseItem {
  id: string
  case_number: string
  category: string
  priority: string
  status: string
  queue: string
  summary: string
  version: number
  created_at: string
}

export interface ChatMessage {
  id: string
  role: 'USER' | 'ASSISTANT' | 'SYSTEM'
  content: string
  language: string
  created_at: string
  channel?: 'CHAT' | 'VOICE'
  is_replay?: boolean
  llm_source?: string
}

export interface VoiceSessionData {
  session_id: string
  conversation_id: string
  ai_identity_disclosed: boolean
  welcome_message: string
}

export interface VoiceTranscriptionData {
  conversation_id: string
  reply_text: string
  reply_audio_url?: string | null
  language: string
  run_id?: string | null
  active_case_id?: string | null
  evidence_summary?: DiscrepancySummary | null
  is_replay?: boolean
  llm_source?: string
}

export interface TraceEvent {
  id?: string
  node?: string
  tool?: string
  status: string
  latency?: number
  input_hash?: string
  output_ref?: any
  timestamp?: string
  type?: string
}

export interface DiscrepancySummary {
  expected_net: string
  observed_net: string
  discrepancy: string
  reason_code: string
  source_type: SourceType
  records_checked?: string[]
  calculation_trace?: Record<string, any>
  limitations?: string
  next_action?: string
  metric_1_label?: string
  metric_2_label?: string
  metric_3_label?: string
  metric_1_value?: string
  metric_2_value?: string
  metric_3_value?: string
  case_number?: string
}

export interface CaseEvent {
  id: string
  actor: string
  event_type: string
  from_status: string | null
  to_status: string | null
  visibility: 'INTERNAL' | 'MERCHANT' | string
  payload?: Record<string, any> | null
  created_at: string
}

export interface ApprovalSummary {
  id: string
  action: string
  action_hash: string
  status: string
  decision: string
  case_version: number
  created_at: string
  reason?: string | null
}

export interface CaseDetail extends SupportCaseItem {
  timeline: CaseEvent[]
  pending_approval?: ApprovalSummary | null
}

export interface VerificationResult {
  case_id: string
  status: string
  verification_result: 'PASS' | 'FAIL'
  before_observed: string
  after_observed: string
  expected_net: string
  evidence_timestamp: string
  verifier_role?: string
}

export interface OutcomeMetrics {
  time_to_first_response_seconds: number
  time_to_verified_resolution_minutes: number
  straight_through_processing_rate_percent: number
  total_cases_handled: number
  total_cases_escalated: number
  repeat_explanations_avoided: number
}

export interface IntegrationHealth {
  status: string
  environment: string
  demo_data_mode: boolean
  demo_deterministic: boolean
  llm_provider: string
  voice_provider: string
  payment_provider: {
    active: string
    status: string
    environment: string
  }
  settlement_ops_adapter: string
  services: {
    api: string
    database: string
    verifier_role: string
  }
}

export interface WatchdogAlert {
  alert_id: string
  batch_ref: string
  amount: string
  currency: string
  utr_number: string
  delay_reason: string
  clearing_bank: string
  expected_credit_window: string
  case_number: string
  case_id: string
  severity: 'INFO' | 'WARNING' | 'CRITICAL'
  messages: { [lang: string]: string }
  soundbox_announcement: string
  detected_at: string
  status: string
}

export interface ChargebackDefensePacket {
  case_number: string
  order_id: string
  disputed_amount: string
  merchant_name: string
  merchant_mid: string
  kyc_status: string
  dispute_category: string
  customer_claim: string
  soundbox_proof: {
    device_model: string
    imei: string
    audio_broadcast_time: string
    broadcast_status: string
    voice_language: string
    tower_cell_id: string
  }
  npci_trace: {
    npci_rrn: string
    payer_vpa: string
    auth_code: string
    gateway_status: string
  }
  arbitration_docket_markdown: string
  generated_at: string
  submission_deadline: string
  status: string
}


