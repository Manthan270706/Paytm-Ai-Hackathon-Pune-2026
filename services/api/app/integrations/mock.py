import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel

from app.integrations.base import (
    LLMProvider,
    PaymentProvider,
    ResyncResult,
    SettlementEntryResult,
    SettlementOpsProvider,
    SettlementProvider,
    SpeechToText,
    TextToSpeech,
    TransactionStatusResult,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider generating schema-compliant responses."""

    def __init__(self, canned_responses: dict[str, Any] | None = None) -> None:
        self.canned_responses = canned_responses or {}

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        # If a canned response matches the schema, instantiate it
        schema_name = schema.__name__
        if schema_name in self.canned_responses:
            data = self.canned_responses[schema_name]
            return schema.model_validate(data)

        # Build fallback mock dictionary by inspecting schema field types
        mock_data: dict[str, Any] = {}
        for name, field in schema.model_fields.items():
            ann = field.annotation
            origin = getattr(ann, "__origin__", None)
            if ann is str:
                if "id" in name.lower():
                    mock_data[name] = str(uuid.uuid4())
                elif "intent" in name.lower():
                    mock_data[name] = "SETTLEMENT_MISMATCH"
                else:
                    mock_data[name] = "Mock generated text"
            elif ann is int:
                mock_data[name] = 1
            elif ann is float:
                mock_data[name] = 0.0
            elif ann is bool:
                mock_data[name] = True
            elif ann is Decimal:
                mock_data[name] = Decimal("6000.00")
            elif ann is uuid.UUID:
                mock_data[name] = uuid.uuid4()
            elif ann is datetime:
                mock_data[name] = datetime.now(UTC)
            elif ann is list or origin is list:
                mock_data[name] = []
            elif ann is dict or origin is dict:
                mock_data[name] = {}
            else:
                mock_data[name] = None

        return schema.model_validate(mock_data)


class MockSpeechToText(SpeechToText):
    """Mock speech-to-text transcriber returning golden scenario complaint."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        if language == "mr":
            return "माझा ₹६,००० चा सेटलमेंट का अडकला आहे?"
        elif language == "hi":
            return "मेरा ₹6,000 का सेटलमेंट क्यों रुका हुआ है?"
        return "My ₹6,000 payment is missing from yesterday's settlement."


class MockTextToSpeech(TextToSpeech):
    """Mock text-to-speech engine returning minimal valid synthetic WAV audio."""

    async def synthesize(
        self,
        text: str,
        language: str = "en",
    ) -> bytes:
        # Minimal 44-byte RIFF/WAVE header representing silence
        sample_rate = 16000
        byte_rate = sample_rate * 2
        return (
            b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            + sample_rate.to_bytes(4, "little")
            + byte_rate.to_bytes(4, "little")
            + b"\x02\x00\x10\x00data\x00\x00\x00\x00"
        )


class MockPaymentProvider(PaymentProvider):
    """Mock payment provider matching the frozen ₹6,000 transaction scenario."""

    async def get_transaction_status(
        self,
        provider_txn_id: str | None = None,
        order_id: str | None = None,
    ) -> TransactionStatusResult:
        return TransactionStatusResult(
            provider_txn_id=provider_txn_id or "TXN_78456321",
            order_id=order_id or "ORD_20261112_01",
            amount=Decimal("6000.00"),
            currency="INR",
            status="SUCCESS",
            txn_time=datetime(2026, 11, 12, 14, 30, tzinfo=UTC),
            source_type="SYNTHETIC_DEMO",
        )


class MockSettlementProvider(SettlementProvider):
    """Mock settlement provider returning the observed ₹9,000 batch entry."""

    async def list_entries(
        self,
        batch_ref: str | None = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
    ) -> list[SettlementEntryResult]:
        return [
            SettlementEntryResult(
                entry_id=str(uuid.uuid4()),
                batch_ref=batch_ref or "BATCH_20261112_01",
                transaction_id="TXN_78456320",
                amount=Decimal("9000.00"),
                entry_type="CAPTURE",
                status="SETTLED",
                source_type="SYNTHETIC_DEMO",
                created_at=datetime(2026, 11, 12, 23, 0, tzinfo=UTC),
            )
        ]


class MockSettlementOpsProvider(SettlementOpsProvider):
    """Mock internal Settlement Operations adapter acknowledging re-sync requests."""

    async def request_resync(
        self,
        batch_ref: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> ResyncResult:
        return ResyncResult(
            batch_ref=batch_ref,
            status="ACKNOWLEDGED",
            amount=amount,
            adapter_ref="MOCK_SETTLEMENT_OPS_ACK_2026",
            idempotency_key=idempotency_key,
            source_type="MOCK_SETTLEMENT_OPS",
        )
