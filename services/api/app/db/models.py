import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    Date as SQLDate,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # MERCHANT, SUPPORT_AGENT, SUPERVISOR
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    merchant_memberships: Mapped[list["MerchantUser"]] = relationship(
        "MerchantUser", back_populates="user", cascade="all, delete-orphan"
    )


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    external_mid: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    masked_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    users: Mapped[list["MerchantUser"]] = relationship(
        "MerchantUser", back_populates="merchant", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="merchant", cascade="all, delete-orphan"
    )
    settlement_batches: Mapped[list["SettlementBatch"]] = relationship(
        "SettlementBatch", back_populates="merchant", cascade="all, delete-orphan"
    )
    support_cases: Mapped[list["SupportCase"]] = relationship(
        "SupportCase", back_populates="merchant", cascade="all, delete-orphan"
    )


class MerchantUser(Base):
    __tablename__ = "merchant_users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), index=True, nullable=False
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), default="OWNER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="merchant_memberships")
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="users")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), default="PAYTM", nullable=False)
    provider_txn_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # SUCCESS, FAILED, PENDING
    txn_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), default="SYNTHETIC_DEMO", nullable=False
    )  # PAYTM_STAGING, SYNTHETIC_DEMO
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="transactions")
    settlement_entries: Mapped[list["SettlementEntry"]] = relationship(
        "SettlementEntry", back_populates="transaction"
    )


class FeeRule(Base):
    __tablename__ = "fee_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id"), index=True, nullable=False
    )
    rule_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    flat_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    merchant: Mapped["Merchant"] = relationship("Merchant")


class SettlementBatch(Base):
    __tablename__ = "settlement_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id"), index=True, nullable=False
    )
    batch_ref: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    date: Mapped[date] = mapped_column(SQLDate, nullable=False)
    expected_settlement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    refunds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    net: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="settlement_batches")
    entries: Mapped[list["SettlementEntry"]] = relationship(
        "SettlementEntry", back_populates="batch", cascade="all, delete-orphan"
    )


class SettlementEntry(Base):
    __tablename__ = "settlement_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("settlement_batches.id"), index=True, nullable=False
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id"), index=True, nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    entry_type: Mapped[str] = mapped_column(
        String(50), default="CAPTURE", nullable=False
    )  # CAPTURE, REFUND, FEE, ADJUSTMENT
    status: Mapped[str] = mapped_column(String(50), default="SETTLED", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    batch: Mapped["SettlementBatch"] = relationship("SettlementBatch", back_populates="entries")
    transaction: Mapped["Transaction | None"] = relationship(
        "Transaction", back_populates="settlement_entries"
    )


class SupportCase(Base):
    __tablename__ = "support_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id"), index=True, nullable=False
    )
    case_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), default="SETTLEMENT_MISMATCH", nullable=False
    )
    priority: Mapped[str] = mapped_column(String(10), default="P1", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NEW", index=True, nullable=False)
    queue: Mapped[str] = mapped_column(String(100), default="SETTLEMENT_OPS", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # Optimistic concurrency
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="support_cases")
    events: Mapped[list["CaseEvent"]] = relationship(
        "CaseEvent", back_populates="case", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["Approval"]] = relationship(
        "Approval", back_populates="case", cascade="all, delete-orphan"
    )


class CaseEvent(Base):
    __tablename__ = "case_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_cases.id"), index=True, nullable=False
    )
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    visibility: Mapped[str] = mapped_column(String(50), default="MERCHANT", nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, nullable=False
    )

    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="events")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id"), index=True, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(50), default="CHAT", nullable=False)  # CHAT, VOICE
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    active_case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("support_cases.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # USER, ASSISTANT, SYSTEM
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), index=True, nullable=False
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("support_cases.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="gemini-1.5-flash", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        "ToolExecution", back_populates="agent_run", cascade="all, delete-orphan"
    )


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_runs.id"), index=True, nullable=False
    )
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    latency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_executions")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_cases.id"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    case_version: Mapped[int] = mapped_column(Integer, nullable=False)
    action_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    decision: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="approvals")


class ResyncRequest(Base):
    __tablename__ = "resync_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_cases.id"), index=True, nullable=False
    )
    batch_ref: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="REQUESTED", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    adapter_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class FollowupJob(Base):
    __tablename__ = "followup_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_cases.id"), index=True, nullable=False
    )
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class LLMCache(Base):
    __tablename__ = "llm_cache"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), index=True, nullable=False
    )
    consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), default="PAYTM", nullable=False)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PROCESSED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, nullable=False
    )
