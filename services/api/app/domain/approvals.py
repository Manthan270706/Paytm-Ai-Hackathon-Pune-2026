"""Checks for safely resuming an approved human-gated action."""

import hashlib
import hmac
import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.core.auth import VALID_ROLES
from app.core.exceptions import ConflictError, ForbiddenError
from app.db.models import Approval, SupportCase, User
from app.domain.policy import evaluate


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def compute_action_hash(action_type: str, parameters: Mapping[str, Any]) -> str:
    """Hash canonical action type and parameters for request and resume checks."""
    normalized_type = action_type.strip().upper()
    canonical = json.dumps(
        {"action_type": normalized_type, "parameters": _json_value(parameters)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _action_payload(action: str) -> tuple[str, dict[str, Any]]:
    raw_action = action.strip()
    if raw_action.startswith("{"):
        try:
            payload = json.loads(raw_action)
        except json.JSONDecodeError as exc:
            raise ConflictError("Approval action payload is invalid") from exc
        if not isinstance(payload, dict):
            raise ConflictError("Approval action payload must be an object")
        action_type = payload.get("action_type", payload.get("type"))
        parameters = payload.get("parameters", {})
        if not isinstance(action_type, str) or not isinstance(parameters, dict):
            raise ConflictError("Approval action payload is incomplete")
        return action_type.strip().upper(), parameters
    if not raw_action:
        raise ConflictError("Approval action is missing")
    return raw_action.upper(), {}


def validate_resume(
    approval: Approval,
    case: SupportCase,
    reviewer: User,
    action: str,
) -> None:
    """Re-check reviewer, case version, action fingerprint and current policy.

    ``action`` is either the action type or a JSON string with ``action_type``
    and ``parameters``. The same canonical payload must be used when initially
    storing ``Approval.action_hash`` and when resuming the approval.
    """
    role = str(getattr(reviewer, "role", "") or "").upper()
    if role not in {"SUPPORT_AGENT", "SUPERVISOR"} or role not in VALID_ROLES:
        raise ForbiddenError("Reviewer role cannot approve this action")
    if getattr(reviewer, "is_active", True) is not True:
        raise ForbiddenError("Inactive users cannot approve actions")

    if approval.case_version != case.version:
        raise ConflictError(
            "Approval is stale because the case version changed",
            details={"approval_version": approval.case_version, "case_version": case.version},
        )

    decision_status = str(getattr(approval, "decision", "PENDING") or "PENDING").upper()
    approval_status = str(getattr(approval, "status", "ACTIVE") or "ACTIVE").upper()
    if decision_status == "REJECTED" or approval_status not in {"ACTIVE", "PENDING"}:
        raise ForbiddenError("Rejected or inactive approval cannot be resumed")

    action_type, parameters = _action_payload(action)
    approved_action_type = str(getattr(approval, "action", "") or "").strip().upper()
    if action_type != approved_action_type:
        raise ConflictError("Approval action type changed")

    expected_hash = compute_action_hash(action_type, parameters)
    stored_hash = str(getattr(approval, "action_hash", "") or "")
    if not stored_hash or not hmac.compare_digest(stored_hash, expected_hash):
        raise ConflictError("Approval action parameters changed")

    policy_context = parameters.get("policy_context", parameters)
    if not isinstance(policy_context, dict):
        raise ForbiddenError("Approval is missing current policy context")
    current_policy = evaluate(action_type, policy_context)
    if current_policy.decision == "DENY":
        raise ForbiddenError(
            "Current policy denies this action",
            details={"reason_code": current_policy.reason_code},
        )
