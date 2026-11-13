from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Tool 1: get_merchant_context
# ------------------------------------------------------------------------------
class GetMerchantContextInput(BaseModel):
    """No inputs; merchant scope is bound server-side from session."""

    pass


class GetMerchantContextOutput(BaseModel):
    mid: str | None
    display_name: str
    status: str
    preferred_language: str
    source_type: str = "SYNTHETIC_DEMO"


# ------------------------------------------------------------------------------
# Tool 2: find_transactions
# ------------------------------------------------------------------------------
class FindTransactionsInput(BaseModel):
    transaction_date: date | None = Field(default=None, description="Date of payment")
    amount: Decimal | None = Field(default=None, description="Exact INR amount")
    order_id: str | None = Field(default=None, description="Paytm or Merchant Order ID")
    transaction_id: str | None = Field(default=None, description="Provider Transaction ID")


class TransactionRecord(BaseModel):
    id: str
    order_id: str
    provider_txn_id: str
    amount: Decimal
    currency: str = "INR"
    status: str
    txn_time: datetime
    source_type: str


class FindTransactionsOutput(BaseModel):
    transactions: list[TransactionRecord]
    source_ids: list[str]


# ------------------------------------------------------------------------------
# Tool 3: get_settlement_entries
# ------------------------------------------------------------------------------
class GetSettlementEntriesInput(BaseModel):
    start_date: date | None = Field(default=None, description="Start date for settlement query")
    end_date: date | None = Field(default=None, description="End date for settlement query")
    batch_ref: str | None = Field(default=None, description="Settlement batch reference ID")


class SettlementEntryRecord(BaseModel):
    id: str
    batch_ref: str
    transaction_id: str | None
    amount: Decimal
    entry_type: str
    status: str
    source_type: str


class GetSettlementEntriesOutput(BaseModel):
    entries: list[SettlementEntryRecord]
    source_ids: list[str]


# ------------------------------------------------------------------------------
# Tool 4: calculate_discrepancy
# ------------------------------------------------------------------------------
class CalculateDiscrepancyInput(BaseModel):
    transaction_ids: list[str] = Field(
        default_factory=list, description="IDs of transactions to reconcile"
    )
    settlement_entry_ids: list[str] = Field(
        default_factory=list, description="IDs of settlement entries to reconcile"
    )


class CalculateDiscrepancyOutput(BaseModel):
    expected_net: Decimal
    observed: Decimal
    discrepancy: Decimal
    reason_code: str
    trace: dict[str, Any]
    source_ids: list[str]


# ------------------------------------------------------------------------------
# Tool 5: create_support_case
# ------------------------------------------------------------------------------
class CreateSupportCaseInput(BaseModel):
    category: str = Field(description="Issue category, e.g. SETTLEMENT_DELAY, TRANSACTION_QUERY")
    summary: str = Field(description="Summary of merchant issue")
    priority: str = Field(default="P2", description="Priority level P1/P2/P3")
    evidence_record_ids: list[str] = Field(default_factory=list, description="Linked record IDs")
    idempotency_key: str | None = Field(default=None, description="Client idempotency key")


class CreateSupportCaseOutput(BaseModel):
    case_id: str
    case_number: str
    status: str
    queue: str


# ------------------------------------------------------------------------------
# Tool 6: assign_case
# ------------------------------------------------------------------------------
class AssignCaseInput(BaseModel):
    case_id: str = Field(description="Target support case ID")
    queue: str = Field(description="Queue to assign: SETTLEMENTS, TECH_SUPPORT, ESCALATIONS")
    reason: str | None = Field(default=None, description="Routing rationale")


class AssignCaseOutput(BaseModel):
    case_id: str
    queue: str
    status: str


# ------------------------------------------------------------------------------
# Tool 7: request_approval
# ------------------------------------------------------------------------------
class RequestApprovalInput(BaseModel):
    case_id: str = Field(description="Target support case ID")
    action: str = Field(description="Action requiring approval, e.g. SETTLEMENT_RESYNC")
    amount: Decimal | None = Field(default=None, description="Financial amount involved if any")
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Evidence payload for human reviewer"
    )


class RequestApprovalOutput(BaseModel):
    approval_id: str
    case_id: str
    status: str = "PENDING"
    case_version: int
    action_hash: str


# ------------------------------------------------------------------------------
# Tool 8: request_settlement_resync
# ------------------------------------------------------------------------------
class RequestSettlementResyncInput(BaseModel):
    case_id: str = Field(description="Target support case ID")
    batch_ref: str = Field(description="Settlement batch reference to re-sync")
    amount: Decimal = Field(description="Re-sync amount")
    idempotency_key: str = Field(description="Unique key to prevent duplicate re-sync execution")


class RequestSettlementResyncOutput(BaseModel):
    resync_id: str
    case_id: str
    batch_ref: str
    status: str
    adapter_ref: str


# ------------------------------------------------------------------------------
# Tool 9: apply_case_update
# ------------------------------------------------------------------------------
class ApplyCaseUpdateInput(BaseModel):
    case_id: str = Field(description="Target support case ID")
    to_status: str = Field(description="Target status in case lifecycle state machine")
    expected_version: int = Field(description="Current version for optimistic concurrency check")
    note: str = Field(description="Audit note for case timeline")


class ApplyCaseUpdateOutput(BaseModel):
    case_id: str
    status: str
    version: int


# ------------------------------------------------------------------------------
# Tool 10: verify_resolution
# ------------------------------------------------------------------------------
class VerifyResolutionInput(BaseModel):
    case_id: str = Field(description="Target support case ID")
    rule: str = Field(
        default="RECONCILE_DISCREPANCY_ZERO",
        description="Verification rule to assert against read-only database",
    )


class VerifyResolutionOutput(BaseModel):
    status: str  # PASS / FAIL
    before: Decimal
    after: Decimal
    evidence_timestamp: datetime


# ------------------------------------------------------------------------------
# Tool 11: send_merchant_update
# ------------------------------------------------------------------------------
class SendMerchantUpdateInput(BaseModel):
    case_id: str = Field(description="Target support case ID")
    template: str = Field(description="Notification template identifier")
    language: str = Field(default="en", description="Target language: en, hi, mr")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Template replacement variables"
    )


class SendMerchantUpdateOutput(BaseModel):
    message_id: str
    channel: str
    delivered: bool
