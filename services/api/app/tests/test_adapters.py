from decimal import Decimal

import pytest
from pydantic import BaseModel

from app.integrations import (
    LLMProvider,
    MockLLMProvider,
    MockPaymentProvider,
    MockSettlementOpsProvider,
    MockSettlementProvider,
    MockSpeechToText,
    MockTextToSpeech,
    PaymentProvider,
    ResyncResult,
    SettlementEntryResult,
    SettlementOpsProvider,
    SettlementProvider,
    SpeechToText,
    TextToSpeech,
    TransactionStatusResult,
    get_llm_provider,
    get_payment_provider,
    get_settlement_ops_provider,
    get_settlement_provider,
    get_stt_provider,
    get_tts_provider,
)


class SampleClassification(BaseModel):
    intent: str
    confidence: float
    is_settlement_issue: bool


@pytest.mark.asyncio
async def test_adapter_inheritance() -> None:
    assert issubclass(MockLLMProvider, LLMProvider)
    assert issubclass(MockSpeechToText, SpeechToText)
    assert issubclass(MockTextToSpeech, TextToSpeech)
    assert issubclass(MockPaymentProvider, PaymentProvider)
    assert issubclass(MockSettlementProvider, SettlementProvider)
    assert issubclass(MockSettlementOpsProvider, SettlementOpsProvider)


@pytest.mark.asyncio
async def test_mock_llm_provider() -> None:
    provider = MockLLMProvider()
    result = await provider.generate_structured(
        prompt="Why is my payout delayed?",
        schema=SampleClassification,
    )
    assert isinstance(result, SampleClassification)
    assert result.intent == "PAYOUT_DELAY"
    assert result.is_settlement_issue is True

    # Canned response support
    canned = MockLLMProvider(
        canned_responses={
            "SampleClassification": {
                "intent": "CUSTOM_INTENT",
                "confidence": 0.99,
                "is_settlement_issue": False,
            }
        }
    )
    canned_res = await canned.generate_structured(
        prompt="Hi",
        schema=SampleClassification,
    )
    assert canned_res.intent == "CUSTOM_INTENT"
    assert canned_res.confidence == 0.99
    assert canned_res.is_settlement_issue is False


@pytest.mark.asyncio
async def test_mock_speech_to_text() -> None:
    stt = MockSpeechToText()
    en_res = await stt.transcribe(b"dummy_wav_data", language="en")
    assert "₹6,000" in en_res

    hi_res = await stt.transcribe(b"dummy_wav_data", language="hi")
    assert "₹6,000" in hi_res

    mr_res = await stt.transcribe(b"dummy_wav_data", language="mr")
    assert "₹६,०००" in mr_res


@pytest.mark.asyncio
async def test_mock_text_to_speech() -> None:
    tts = MockTextToSpeech()
    audio_bytes = await tts.synthesize("Your ticket has been created.")
    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) >= 44
    assert audio_bytes.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_mock_payment_provider() -> None:
    provider = MockPaymentProvider()
    txn = await provider.get_transaction_status(provider_txn_id="TXN_12345")
    assert isinstance(txn, TransactionStatusResult)
    assert txn.provider_txn_id == "TXN_12345"
    assert txn.amount == Decimal("6000.00")
    assert txn.status == "SUCCESS"
    assert txn.source_type == "SYNTHETIC_DEMO"


@pytest.mark.asyncio
async def test_mock_settlement_provider() -> None:
    provider = MockSettlementProvider()
    entries = await provider.list_entries(batch_ref="BATCH_01")
    assert len(entries) == 1
    assert isinstance(entries[0], SettlementEntryResult)
    assert entries[0].batch_ref == "BATCH_01"
    assert entries[0].amount == Decimal("9000.00")
    assert entries[0].source_type == "SYNTHETIC_DEMO"


@pytest.mark.asyncio
async def test_mock_settlement_ops_provider() -> None:
    ops = MockSettlementOpsProvider()
    res = await ops.request_resync(
        batch_ref="BATCH_01",
        amount=Decimal("6000.00"),
        idempotency_key="resync_case_uuid",
    )
    assert isinstance(res, ResyncResult)
    assert res.status == "ACKNOWLEDGED"
    assert res.amount == Decimal("6000.00")
    assert res.source_type == "MOCK_SETTLEMENT_OPS"


def test_factories() -> None:
    assert isinstance(get_llm_provider("mock"), LLMProvider)
    assert isinstance(get_llm_provider("groq_direct"), LLMProvider)
    assert isinstance(get_llm_provider("local_direct"), LLMProvider)
    assert isinstance(get_llm_provider("ollama_direct"), LLMProvider)
    assert isinstance(get_stt_provider("mock"), SpeechToText)
    assert isinstance(get_tts_provider("mock"), TextToSpeech)
    assert isinstance(get_payment_provider("mock"), PaymentProvider)
    assert isinstance(get_settlement_provider("mock"), SettlementProvider)
    assert isinstance(get_settlement_ops_provider("mock"), SettlementOpsProvider)


@pytest.mark.asyncio
async def test_groq_and_local_llm_adapters() -> None:
    from app.integrations import GroqLLMProvider, LocalLLMProvider, OllamaLLMProvider, FallbackLLMProvider

    assert issubclass(GroqLLMProvider, LLMProvider)
    assert issubclass(LocalLLMProvider, LLMProvider)
    assert issubclass(OllamaLLMProvider, LLMProvider)
    assert issubclass(FallbackLLMProvider, LLMProvider)

    # Groq without API key raises ValueError
    groq = GroqLLMProvider(api_key="")
    with pytest.raises(ValueError, match="GROQ_API_KEY is not configured"):
        await groq.generate_structured("test", SampleClassification)

    # Local LLM liveness probe returns False when offline without throwing unhandled exception
    local = LocalLLMProvider(base_url="http://127.0.0.1:59999/v1")
    is_live = await local.is_available()
    assert is_live is False

    # Ollama provider offline probe and warmup
    ollama = OllamaLLMProvider(base_url="http://127.0.0.1:59998")
    assert await ollama.is_available() is False
    assert await ollama.warmup() is False

    # Fallback chain with dynamic LLM_CASCADE
    fallback = FallbackLLMProvider()
    fallback.ollama = ollama
    fallback.local = ollama
    fallback.groq = groq
    fallback.gemini.api_key = None
    assert "ollama" in fallback.cascade_tiers

    res = await fallback.generate_structured("Hi", SampleClassification)
    assert isinstance(res, SampleClassification)
    assert len(fallback.tier_history) > 0


