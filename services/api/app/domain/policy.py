from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicyDecision(BaseModel):
    """Deterministic policy evaluation decision."""

    decision: Literal["ALLOW", "REQUIRE_APPROVAL", "DENY"]
    reason_code: str = Field(description="Policy rationale / rule identifier")


def evaluate(
    action: str,
    context: dict[str, Any],
) -> PolicyDecision:
    """Evaluate operational action against policy rules.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C2.
    """
    raise NotImplementedError("TODO(core): Codex task P2-C2")
