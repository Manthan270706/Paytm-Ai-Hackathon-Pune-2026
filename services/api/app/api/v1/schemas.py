import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Auth Schemas
# ------------------------------------------------------------------------------
class DemoLoginRequest(BaseModel):
    role: str = Field(
        default="MERCHANT", description="Role to log in as: MERCHANT, SUPPORT_AGENT, or SUPERVISOR"
    )
    email: str | None = Field(default=None, description="Optional specific user email")


class DemoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: uuid.UUID
    merchant_id: uuid.UUID | None
    display_name: str


class CurrentUserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    is_active: bool
    preferred_language: str
    allowed_merchant_ids: list[uuid.UUID]
    active_merchant_id: uuid.UUID | None


# ------------------------------------------------------------------------------
# Merchant Schemas
# ------------------------------------------------------------------------------
class MerchantSummaryResponse(BaseModel):
    id: uuid.UUID
    external_mid: str | None
    display_name: str
    masked_phone: str
    status: str
    created_at: datetime
    pending_settlement_amount: Decimal = Field(default=Decimal("0.00"))
    open_cases_count: int = 0


# ------------------------------------------------------------------------------
# Transaction Schemas
# ------------------------------------------------------------------------------
class TransactionItemResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    provider: str
    provider_txn_id: str
    order_id: str
    amount: Decimal
    currency: str
    status: str
    txn_time: datetime
    source_type: str


class TransactionDetailResponse(TransactionItemResponse):
    settlement_status: str | None = None
    settlement_batch_ref: str | None = None


# ------------------------------------------------------------------------------
# Settlement Schemas
# ------------------------------------------------------------------------------
class SettlementEntryResponse(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    transaction_id: uuid.UUID | None
    amount: Decimal
    entry_type: str
    status: str
    source_type: str
    created_at: datetime


class SettlementBatchResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    batch_ref: str
    date: date
    expected_settlement_date: datetime
    gross: Decimal
    fees: Decimal
    refunds: Decimal
    net: Decimal
    status: str
    source_type: str
    entries_count: int = 0


# ------------------------------------------------------------------------------
# Agent & Conversation Schemas
# ------------------------------------------------------------------------------
class AgentMessageRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str
    channel: str = Field(default="CHAT", description="CHAT or VOICE")
    language: str = Field(default="en", description="en, hi, or mr")


class AgentMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    run_id: uuid.UUID
    reply: str
    language: str
    intent: str
    active_case_id: uuid.UUID | None = None
    evidence_summary: dict[str, Any] | None = None
    is_replay: bool = False
    llm_source: str = "SYNTHETIC_DEMO"


# ------------------------------------------------------------------------------
# Voice Schemas
# ------------------------------------------------------------------------------
class VoiceSessionRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    language: str = "en"


class VoiceSessionResponse(BaseModel):
    session_id: uuid.UUID
    conversation_id: uuid.UUID
    ai_identity_disclosed: bool = True
    welcome_message: str


class VoiceTranscriptionRequest(BaseModel):
    conversation_id: uuid.UUID
    transcript: str
    language: str = "en"


class VoiceTranscriptionResponse(BaseModel):
    conversation_id: uuid.UUID
    reply_text: str
    reply_audio_url: str | None = None
    language: str
    run_id: uuid.UUID | None = None
    active_case_id: uuid.UUID | None = None
    evidence_summary: dict[str, Any] | None = None
    is_replay: bool = False
    llm_source: str = "SYNTHETIC_DEMO"


# ------------------------------------------------------------------------------
# Support Case Schemas
# ------------------------------------------------------------------------------
class CaseCreateRequest(BaseModel):
    category: str = "SETTLEMENT_MISMATCH"
    priority: str = "P1"
    summary: str
    evidence_refs: dict[str, Any] | None = None


class CaseEventResponse(BaseModel):
    id: uuid.UUID
    actor: str
    event_type: str
    from_status: str | None
    to_status: str | None
    visibility: str
    payload: dict[str, Any] | None
    created_at: datetime


class CaseItemResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    case_number: str
    category: str
    priority: str
    status: str
    queue: str
    summary: str
    version: int
    created_at: datetime
    updated_at: datetime


class ApprovalSummaryResponse(BaseModel):
    id: uuid.UUID
    action: str
    action_hash: str
    status: str
    decision: str
    case_version: int
    created_at: datetime
    reason: str | None = None


class CaseDetailResponse(CaseItemResponse):
    timeline: list[CaseEventResponse] = []
    pending_approval: ApprovalSummaryResponse | None = None


class CaseApproveRequest(BaseModel):
    expected_version: int
    action_hash: str
    reason: str | None = None


class CaseRejectRequest(BaseModel):
    expected_version: int
    action_hash: str
    reason: str


class CaseAssignRequest(BaseModel):
    expected_version: int
    queue: str


class CaseResolveRequest(BaseModel):
    expected_version: int | None = None
    reason: str | None = None


class CaseVerifyResponse(BaseModel):
    case_id: uuid.UUID
    status: str
    verification_result: str  # PASS or FAIL
    before_observed: Decimal
    after_observed: Decimal
    expected_net: Decimal
    evidence_timestamp: datetime
    verifier_role: str = "opssaathi_verifier"


# ------------------------------------------------------------------------------
# Demo Control Schemas
# ------------------------------------------------------------------------------
class SimulateSettlementRequest(BaseModel):
    case_id: uuid.UUID | None = None
    amount: Decimal = Decimal("6000.00")
    batch_ref: str = "BATCH_20261112_01"


class SimulateSettlementResponse(BaseModel):
    message: str
    added_entry_id: uuid.UUID
    amount: Decimal
    source_type: str = "SYNTHETIC_DEMO"


class DemoResetResponse(BaseModel):
    message: str
    seeded_merchant_id: uuid.UUID
    expected_net: Decimal
    observed_net: Decimal
    discrepancy: Decimal
    status: str


# ------------------------------------------------------------------------------
# Metrics & Webhooks Schemas
# ------------------------------------------------------------------------------
class OutcomeMetricsResponse(BaseModel):
    time_to_first_response_seconds: float
    time_to_verified_resolution_minutes: float
    straight_through_processing_rate_percent: float
    total_cases_handled: int
    total_cases_escalated: int
    repeat_explanations_avoided: int


class PaytmWebhookPayload(BaseModel):
    event_id: str
    provider_txn_id: str
    order_id: str
    amount: Decimal
    status: str
    checksum: str
