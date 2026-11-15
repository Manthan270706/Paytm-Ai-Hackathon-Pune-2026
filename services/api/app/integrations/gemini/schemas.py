from pydantic import BaseModel, Field


class EntityExtractionResult(BaseModel):
    """Structured extraction of entities from merchant complaint text."""

    amount: str | None = Field(
        default=None, description="Monetary amount in INR extracted from user message"
    )
    reference: str | None = Field(
        default=None, description="Transaction, order, or batch reference"
    )
    category: str = Field(
        default="SETTLEMENT_MISMATCH", description="Primary complaint category"
    )
    missing_fields: list[str] = Field(
        default_factory=list, description="Fields required to proceed that are missing"
    )


class IntentClassificationResult(BaseModel):
    """Structured classification of merchant operational intent."""

    intent: str = Field(
        default="SETTLEMENT_MISMATCH",
        description="Intent code: GREETING, GENERAL_QUERY, SETTLEMENT_MISMATCH, REFUND_DISPUTE, FEE_OVERCHARGE, HARDWARE_DIAGNOSTICS, PAYOUT_DELAY",
    )
    confidence: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(default="", description="Brief chain-of-thought justification")


class ConversationalResponse(BaseModel):
    """Structured response for greetings, capability queries, and conversational turns."""

    reply: str = Field(
        description="Warm, empathetic response in the merchant's language as OpsSaathi AI operations teammate"
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested operational topics the merchant can explore (e.g. settlements, refunds, soundbox)",
    )
