"""Deterministic action policy for merchant support workflows."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.config import settings


class PolicyDecision(BaseModel):
    """Deterministic policy evaluation decision."""

    decision: Literal["ALLOW", "REQUIRE_HUMAN_APPROVAL", "DENY"]
    reason_code: str = Field(description="Policy rationale / rule identifier")


def _decision(
    decision: Literal["ALLOW", "REQUIRE_HUMAN_APPROVAL", "DENY"], reason: str
) -> PolicyDecision:
    return PolicyDecision(decision=decision, reason_code=reason)


def _decimal_amount(value: Any) -> Decimal | None:
    if isinstance(value, (bool, float)) or value is None:
        return None
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not amount.is_finite() or amount < 0:
        return None
    return amount


def evaluate(action: str, context: dict[str, Any]) -> PolicyDecision:
    """Evaluate an action against fixed server-side rules and configuration.

    Context contains backend-derived evidence and authorization facts. Unknown
    actions and incomplete evidence are denied by default.
    """
    normalized_action = action.strip().upper() if isinstance(action, str) else ""

    if normalized_action in {"READ_OWN_TRANSACTION_STATUS", "READ_TRANSACTION_STATUS"}:
        if context.get("authenticated") is not True:
            return _decision("DENY", "AUTHENTICATION_REQUIRED")
        if context.get("tenant_scoped") is not True:
            return _decision("DENY", "TENANT_SCOPE_REQUIRED")
        return _decision("ALLOW", "OWN_TRANSACTION_READ_ALLOWED")

    if normalized_action == "CALCULATE_DISCREPANCY":
        evidence_present = context.get(
            "required_source_records_present", context.get("source_records_present", False)
        )
        if evidence_present is not True:
            return _decision("DENY", "SOURCE_RECORDS_REQUIRED")
        return _decision("ALLOW", "DETERMINISTIC_RECONCILIATION_ALLOWED")

    if normalized_action == "CREATE_SUPPORT_CASE":
        return _decision("ALLOW", "LOW_RISK_CASE_CREATION")

    if normalized_action == "ASSIGN_INTERNAL_QUEUE":
        role = str(context.get("actor_role", context.get("role", ""))).upper()
        if role in {"SUPPORT_AGENT", "SUPERVISOR"} or context.get("approved_workflow") is True:
            return _decision("ALLOW", "SUPPORT_ASSIGNMENT_ALLOWED")
        return _decision("DENY", "SUPPORT_ROLE_REQUIRED")

    if normalized_action == "IN_APP_STATUS_UPDATE":
        if context.get("approved_template") is not True:
            return _decision("DENY", "APPROVED_TEMPLATE_REQUIRED")
        if context.get("contains_sensitive_data") is True:
            return _decision("DENY", "SENSITIVE_DATA_PROHIBITED")
        return _decision("ALLOW", "SAFE_STATUS_UPDATE_ALLOWED")

    if normalized_action in {"SETTLEMENT_RESYNC", "REQUEST_SETTLEMENT_RESYNC"}:
        amount = _decimal_amount(context.get("discrepancy", context.get("amount")))
        if amount is None:
            return _decision("DENY", "VALID_DISCREPANCY_REQUIRED")
        threshold = settings.RESYNC_APPROVAL_THRESHOLD_INR
        if amount <= threshold:
            return _decision("ALLOW", "RESYNC_WITHIN_APPROVAL_THRESHOLD")
        return _decision("REQUIRE_HUMAN_APPROVAL", "RESYNC_EXCEEDS_APPROVAL_THRESHOLD")

    if normalized_action in {"INITIATE_REFUND", "REFUND"}:
        return _decision("REQUIRE_HUMAN_APPROVAL", "REFUND_REQUIRES_HUMAN_APPROVAL")

    if normalized_action in {"TRANSFER_FUNDS", "CHANGE_BANK_DETAILS"}:
        return _decision("DENY", "FINANCIAL_ACTION_OUT_OF_SCOPE")

    if normalized_action in {"CLOSE_CASE", "RESOLVE_CASE"}:
        if context.get("verification_passed") is True:
            return _decision("ALLOW", "INDEPENDENT_VERIFICATION_PASSED")
        return _decision("DENY", "VERIFICATION_PASS_REQUIRED")

    if normalized_action == "OUTBOUND_PHONE_CALL":
        if context.get("consent") is not True:
            return _decision("DENY", "CALL_CONSENT_REQUIRED")
        if context.get("provider_configured") is not True:
            return _decision("DENY", "CALL_PROVIDER_UNAVAILABLE")
        return _decision("ALLOW", "CONSENTED_CALL_PROVIDER_CONFIGURED")

    return _decision("DENY", "UNKNOWN_ACTION")
