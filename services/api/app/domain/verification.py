import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


class VerificationResult(BaseModel):
    """Result of independent read-only resolution verification."""

    status: Literal["PASS", "FAIL"] = Field(
        description="Verification outcome: PASS if discrepancy eliminated, else FAIL"
    )
    before: Decimal = Field(description="Discrepancy amount before action")
    after: Decimal = Field(description="Discrepancy amount after action")
    evidence_timestamp: datetime = Field(
        description="Timestamp when verifier session observed the ground truth"
    )


async def verify_resolution(
    case_id: uuid.UUID,
    rule: str,
    verifier_session: AsyncSession,
    now: datetime,
) -> VerificationResult:
    """Perform independent read-only database query to verify resolution.

    Executes strictly against the read-only verifier session (no writes permitted).

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P3-C2.
    """
    raise NotImplementedError("TODO(core): Codex task P3-C2")
