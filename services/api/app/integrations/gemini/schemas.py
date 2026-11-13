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
        description="Intent code: SETTLEMENT_MISMATCH, REFUND_INQUIRY, PAYOUT_DELAY",
    )
    confidence: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(default="", description="Brief chain-of-thought justification")
