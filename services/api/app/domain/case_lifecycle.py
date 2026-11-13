from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import ConflictError, ForbiddenError  # noqa: F401
from app.db.models import SupportCase


class CaseTransition(BaseModel):
    """Result of state transition on a support case."""

    new_status: str
    new_version: int
    event: dict[str, Any] = Field(default_factory=dict)


def transition(
    case: SupportCase,
    to_status: str,
    expected_version: int,
    actor: str,
) -> CaseTransition:
    """Validate and perform case state transition with optimistic locking.

    Raises ConflictError on version mismatch.
    Raises ForbiddenError on invalid state machine transition.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C2.
    """
    raise NotImplementedError("TODO(core): Codex task P2-C2")
