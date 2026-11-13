export type SourceType = 'PAYTM_STAGING' | 'SYNTHETIC_DEMO' | 'MOCK' | 'MOCK_SETTLEMENT_OPS'

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
}
