import re
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
        session: Any | None = None,
    ) -> T:
        # If a canned response matches the schema, instantiate it
        schema_name = schema.__name__
        if schema_name in self.canned_responses:
            data = self.canned_responses[schema_name]
            return schema.model_validate(data)

        # Handle ConversationalResponse directly
        prompt_lower = prompt.lower()
        if schema_name == "ConversationalResponse":
            if "mr" in prompt_lower or any(w in prompt for w in ["नमस्कार", "कशी", "आहे"]):
                reply = (
                    "नमस्कार! मी ऑप्ससाथी (OpsSaathi) आहे, तुमचा स्वायत्त पेटीएम मर्चंट ऑपरेशन्स साथी. "
                    "मी सेटलमेंट तफावत, दुहेरी रिफंड डेबिट, MDR फी, साउंडबॉक्स किंवा पेआउट तपासणीत मदत करू शकतो. "
                    "मी आज तुम्हाला कशी मदत करू?"
                )
            elif "hi" in prompt_lower or any(w in prompt for w in ["नमस्ते", "कैसे", "मदद"]):
                reply = (
                    "नमस्ते! मैं ऑप्ससाथी (OpsSaathi) हूँ, आपका स्वायत्त पेटीएम मर्चेंट ऑपरेशन्स साथी। "
                    "मैं सेटलमेंट, रिफंड विवाद, MDR शुल्क अंतर, साउंडबॉक्स जांच या पेआउट में देरी जैसी समस्याओं को सुलझाने में सहायता करता हूँ। "
                    "आज मैं आपकी क्या मदद करूँ?"
                )
            else:
                reply = (
                    "Hello! I am OpsSaathi, your autonomous Paytm Merchant Operations Teammate. "
                    "I can help investigate missing settlements, duplicate refund debits, MDR fee variances, "
                    "Soundbox telemetry diagnostics, or delayed payouts. How can I assist your business today?"
                )
            return schema.model_validate({
                "reply": reply,
                "suggested_actions": ["Missing Settlement", "Refund Dispute", "MDR Overcharge", "Soundbox Check", "Payout Delay"],
            })

        # Build fallback mock dictionary by inspecting schema field types
        detected_intent = "SETTLEMENT_MISMATCH"
        has_operational_keyword = any(
            k in prompt_lower
            for k in [
                "settlement", "missing", "refund", "debited", "mdr", "fee", "rupay",
                "soundbox", "hardware", "audio", "latency", "chime", "payout", "delay",
                "hold", "sla", "6000", "1200", "850", "18500", "ord_", "batch_", "txn_",
            ]
        )

        if not has_operational_keyword and (
            re.search(r"\b(hi|hello|hey|heyy+|howdy|greetings|namaste|namaskar|good\s*(morning|afternoon|evening)|who\s+are\s+you|who\s+is\s+this)\b", prompt_lower)
            or any(w in prompt for w in ["नमस्ते", "नमस्कार", "प्रणाम", "हाय", "हॅलो", "कोण", "कौन"])
        ):
            detected_intent = "GREETING"
        elif not has_operational_keyword and (
            "help" in prompt_lower or "what can you do" in prompt_lower or "features" in prompt_lower
            or any(w in prompt for w in ["मदद", "काय करू शकता", "क्या कर सकते"])
        ):
            detected_intent = "GENERAL_QUERY"
        elif "refund" in prompt_lower or "debited" in prompt_lower or "1025" in prompt_lower:
            detected_intent = "REFUND_DISPUTE"
        elif "mdr" in prompt_lower or "fee" in prompt_lower or "rupay" in prompt_lower or "1026" in prompt_lower:
            detected_intent = "FEE_OVERCHARGE"
        elif "soundbox" in prompt_lower or "hardware" in prompt_lower or "audio" in prompt_lower or "1027" in prompt_lower:
            detected_intent = "HARDWARE_DIAGNOSTICS"
        elif "payout" in prompt_lower or "delay" in prompt_lower or "hold" in prompt_lower or "1028" in prompt_lower:
            detected_intent = "PAYOUT_DELAY"
        elif "settlement" in prompt_lower or "missing" in prompt_lower or "6000" in prompt_lower or "1024" in prompt_lower:
            detected_intent = "SETTLEMENT_MISMATCH"

        mock_data: dict[str, Any] = {}
        for name, field in schema.model_fields.items():
            ann = field.annotation
            origin = getattr(ann, "__origin__", None)
            if ann is str:
                if "id" in name.lower():
                    mock_data[name] = str(uuid.uuid4())
                elif "intent" in name.lower():
                    mock_data[name] = detected_intent
                elif name == "category":
                    mock_data[name] = detected_intent
                elif name == "amount":
                    if "1200" in prompt_lower or "1,200" in prompt_lower:
                        mock_data[name] = "1200.00"
                    elif "850" in prompt_lower:
                        mock_data[name] = "850.00"
                    elif "18500" in prompt_lower or "18,500" in prompt_lower:
                        mock_data[name] = "18500.00"
                    else:
                        mock_data[name] = "6000.00"
                elif name == "reference":
                    if "ord_20261111_09" in prompt_lower:
                        mock_data[name] = "ORD_20261111_09"
                    elif "batch_20261110_02" in prompt_lower:
                        mock_data[name] = "BATCH_20261110_02"
                    else:
                        mock_data[name] = "ORD_20261112_01"
                else:
                    mock_data[name] = "Mock generated text"
            elif ann is int:
                mock_data[name] = 1
            elif ann is float:
                mock_data[name] = 0.0
            elif ann is bool:
                mock_data[name] = True
            elif ann is Decimal:
                if detected_intent == "REFUND_DISPUTE":
                    mock_data[name] = Decimal("1200.00")
                elif detected_intent == "FEE_OVERCHARGE":
                    mock_data[name] = Decimal("850.00")
                elif detected_intent == "PAYOUT_DELAY":
                    mock_data[name] = Decimal("18500.00")
                elif detected_intent == "HARDWARE_DIAGNOSTICS":
                    mock_data[name] = Decimal("0.00")
                else:
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
