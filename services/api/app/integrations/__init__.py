from app.core.config import settings
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
from app.integrations.gemini.provider import (
    FallbackLLMProvider,
    GeminiLLMProvider,
)
from app.integrations.mock import (
    MockLLMProvider,
    MockPaymentProvider,
    MockSettlementOpsProvider,
    MockSettlementProvider,
    MockSpeechToText,
    MockTextToSpeech,
)

__all__ = [
    "LLMProvider",
    "SpeechToText",
    "TextToSpeech",
    "PaymentProvider",
    "SettlementProvider",
    "SettlementOpsProvider",
    "TransactionStatusResult",
    "SettlementEntryResult",
    "ResyncResult",
    "GeminiLLMProvider",
    "FallbackLLMProvider",
    "MockLLMProvider",
    "MockSpeechToText",
    "MockTextToSpeech",
    "MockPaymentProvider",
    "MockSettlementProvider",
    "MockSettlementOpsProvider",
    "get_llm_provider",
    "get_stt_provider",
    "get_tts_provider",
    "get_payment_provider",
    "get_settlement_provider",
    "get_settlement_ops_provider",
]


def get_llm_provider(name: str | None = None) -> LLMProvider:
    provider_name = (name or settings.LLM_PROVIDER).lower()
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "gemini_direct":
        return GeminiLLMProvider()
    return FallbackLLMProvider()


def get_stt_provider(name: str | None = None) -> SpeechToText:
    provider_name = (name or settings.VOICE_PROVIDER).lower()
    if provider_name == "mock":
        return MockSpeechToText()
    return MockSpeechToText()


def get_tts_provider(name: str | None = None) -> TextToSpeech:
    provider_name = (name or settings.VOICE_PROVIDER).lower()
    if provider_name == "mock":
        return MockTextToSpeech()
    return MockTextToSpeech()


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    return MockPaymentProvider()


def get_settlement_provider(name: str | None = None) -> SettlementProvider:
    return MockSettlementProvider()


def get_settlement_ops_provider(name: str | None = None) -> SettlementOpsProvider:
    return MockSettlementOpsProvider()
