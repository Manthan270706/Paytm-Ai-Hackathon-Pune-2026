"""Support case state machine with optimistic version checks."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import ConflictError, ForbiddenError
from app.db.models import SupportCase


class CaseTransition(BaseModel):
    """Result of state transition on a support case."""

    new_status: str
    new_version: int
    event: dict[str, Any] = Field(default_factory=dict)


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"TRIAGED", "ESCALATED", "CANCELLED"},
    "TRIAGED": {"INVESTIGATING", "ESCALATED", "CANCELLED"},
    "INVESTIGATING": {"ACTION_REQUIRED", "IN_PROGRESS", "ESCALATED", "CANCELLED"},
    "ACTION_REQUIRED": {"AWAITING_APPROVAL", "IN_PROGRESS", "ESCALATED", "CANCELLED"},
    "AWAITING_APPROVAL": {"APPROVED", "REJECTED"},
    "APPROVED": {"IN_PROGRESS", "ESCALATED", "CANCELLED"},
    "REJECTED": {"ESCALATED", "CANCELLED"},
    "IN_PROGRESS": {"PENDING_EXTERNAL", "VERIFYING", "ESCALATED", "CANCELLED"},
    "PENDING_EXTERNAL": {"IN_PROGRESS", "VERIFYING", "ESCALATED", "CANCELLED"},
    "VERIFYING": {"RESOLVED", "IN_PROGRESS"},
    "ESCALATED": {"CANCELLED"},
    "RESOLVED": set(),
    "CANCELLED": set(),
}


def _event_value(event: Any, name: str) -> Any:
    if isinstance(event, Mapping):
        return event.get(name)
    return getattr(event, name, None)


def _verification_passed(case: SupportCase) -> bool:
    """Require a recorded verifier PASS before permitting the resolved state."""
    explicit_status = getattr(case, "verification_status", None)
    if isinstance(explicit_status, str) and explicit_status.upper() == "PASS":
        return True

    # Do not trigger a lazy relationship load from this synchronous domain function.
    events = case.__dict__.get("events", ())
    for event in events or ():
        event_type = str(_event_value(event, "event_type") or "").upper()
        payload = _event_value(event, "payload") or {}
        if not isinstance(payload, Mapping):
            continue
        result = payload.get("status", payload.get("result", payload.get("verification_status")))
        if event_type.startswith(("VERIFICATION", "VERIFY")) and str(result).upper() == "PASS":
            return True
    return False


def transition(
    case: SupportCase,
    to_status: str,
    expected_version: int,
    actor: str,
) -> CaseTransition:
    """Validate and apply one allowed state transition.

    Optimistic concurrency is checked before mutation. A RESOLVED transition
    additionally requires an independent verification PASS already recorded on
    the case or its loaded event history.
    """
    current_version = getattr(case, "version", None)
    if current_version != expected_version:
        raise ConflictError(
            "Case version changed",
            details={"expected_version": expected_version, "current_version": current_version},
        )

    current_status = str(getattr(case, "status", "") or "").upper()
    target_status = to_status.strip().upper() if isinstance(to_status, str) else ""
    if not actor or not actor.strip():
        raise ForbiddenError("A case transition requires an identified actor")
    if target_status not in _ALLOWED_TRANSITIONS.get(current_status, set()):
        raise ForbiddenError(f"Transition from {current_status} to {target_status} is not allowed")
    resolving_without_pass = (
        current_status == "VERIFYING"
        and target_status == "RESOLVED"
        and not _verification_passed(case)
    )
    if resolving_without_pass:
        raise ForbiddenError("Case cannot be resolved without independent verification PASS")

    new_version = current_version + 1
    event = {
        "event_type": "CASE_STATUS_CHANGED",
        "actor": actor.strip(),
        "from_status": current_status,
        "to_status": target_status,
        "version": new_version,
    }
    case.status = target_status
    case.version = new_version
    return CaseTransition(new_status=target_status, new_version=new_version, event=event)
