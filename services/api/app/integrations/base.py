import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


# ------------------------------------------------------------------------------
# Provider Result DTOs
# ------------------------------------------------------------------------------
class TransactionStatusResult(BaseModel):
    provider_txn_id: str
    order_id: str
    amount: Decimal
    currency: str = "INR"
    status: str  # SUCCESS, FAILED, PENDING
    txn_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_type: str = "SYNTHETIC_DEMO"  # PAYTM_STAGING, SYNTHETIC_DEMO


class SettlementEntryResult(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_ref: str
    transaction_id: str | None = None
    amount: Decimal
    entry_type: str = "CAPTURE"  # CAPTURE, REFUND, FEE, ADJUSTMENT
    status: str = "SETTLED"
    source_type: str = "SYNTHETIC_DEMO"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResyncResult(BaseModel):
    batch_ref: str
    status: str = "ACKNOWLEDGED"  # ACKNOWLEDGED, FAILED
    amount: Decimal
    adapter_ref: str
    idempotency_key: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_type: str = "MOCK_SETTLEMENT_OPS"


# ------------------------------------------------------------------------------
# Abstract Adapter Interfaces
# ------------------------------------------------------------------------------
class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        session: Any | None = None,
    ) -> T:
        """Generate structured Pydantic response from LLM."""
        pass


class SpeechToText(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        """Transcribe audio bytes to text string."""
        pass


class TextToSpeech(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "en",
    ) -> bytes:
        """Synthesize text into audio bytes."""
        pass


class PaymentProvider(ABC):
    @abstractmethod
    async def get_transaction_status(
        self,
        provider_txn_id: str | None = None,
        order_id: str | None = None,
    ) -> TransactionStatusResult:
        """Look up transaction status by provider txn ID or order ID."""
        pass


class SettlementProvider(ABC):
    @abstractmethod
    async def list_entries(
        self,
        batch_ref: str | None = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
    ) -> list[SettlementEntryResult]:
        """List settlement entries from the settlement provider."""
        pass


class SettlementOpsProvider(ABC):
    @abstractmethod
    async def request_resync(
        self,
        batch_ref: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> ResyncResult:
        """Request cross-system batch re-sync against Settlement Operations."""
        pass
