from decimal import Decimal

import pytest

from app.domain.policy import PolicyDecision, evaluate


def test_policy_decision_model_and_allow_rows() -> None:
    assert evaluate(
        "READ_OWN_TRANSACTION_STATUS", {"authenticated": True, "tenant_scoped": True}
    ) == PolicyDecision(decision="ALLOW", reason_code="OWN_TRANSACTION_READ_ALLOWED")
    assert evaluate(
        "CALCULATE_DISCREPANCY", {"required_source_records_present": True}
    ).decision == "ALLOW"
    assert evaluate("CREATE_SUPPORT_CASE", {}).decision == "ALLOW"
    assert evaluate("ASSIGN_INTERNAL_QUEUE", {"actor_role": "SUPPORT_AGENT"}).decision == "ALLOW"
    assert evaluate(
        "ASSIGN_INTERNAL_QUEUE", {"approved_workflow": True}
    ).decision == "ALLOW"
    assert evaluate(
        "IN_APP_STATUS_UPDATE", {"approved_template": True, "contains_sensitive_data": False}
    ).decision == "ALLOW"


def test_read_and_reconciliation_require_authenticated_scoped_evidence() -> None:
    assert evaluate("READ_TRANSACTION_STATUS", {}).decision == "DENY"
    assert evaluate(
        "READ_TRANSACTION_STATUS", {"authenticated": True, "tenant_scoped": False}
    ).reason_code == "TENANT_SCOPE_REQUIRED"
    assert evaluate("CALCULATE_DISCREPANCY", {}).reason_code == "SOURCE_RECORDS_REQUIRED"


def test_assignment_and_status_update_fail_closed() -> None:
    assert evaluate("ASSIGN_INTERNAL_QUEUE", {"actor_role": "MERCHANT"}).decision == "DENY"
    assert evaluate("IN_APP_STATUS_UPDATE", {}).reason_code == "APPROVED_TEMPLATE_REQUIRED"
    assert evaluate(
        "IN_APP_STATUS_UPDATE", {"approved_template": True, "contains_sensitive_data": True}
    ).reason_code == "SENSITIVE_DATA_PROHIBITED"


def test_resync_threshold_uses_configured_decimal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.domain.policy.settings.RESYNC_APPROVAL_THRESHOLD_INR", Decimal("2500.00")
    )

    at_threshold = evaluate("SETTLEMENT_RESYNC", {"discrepancy": Decimal("2500.00")})
    above_threshold = evaluate("SETTLEMENT_RESYNC", {"discrepancy": Decimal("2500.01")})

    assert at_threshold.decision == "ALLOW"
    assert at_threshold.reason_code == "RESYNC_WITHIN_APPROVAL_THRESHOLD"
    assert above_threshold.decision == "REQUIRE_HUMAN_APPROVAL"
    assert above_threshold.reason_code == "RESYNC_EXCEEDS_APPROVAL_THRESHOLD"


def test_resync_rejects_missing_or_float_money() -> None:
    assert evaluate("SETTLEMENT_RESYNC", {}).reason_code == "VALID_DISCREPANCY_REQUIRED"
    assert evaluate("SETTLEMENT_RESYNC", {"amount": 6000.0}).decision == "DENY"


def test_refund_requires_approval_and_out_of_scope_actions_are_denied() -> None:
    assert evaluate("INITIATE_REFUND", {}).decision == "REQUIRE_HUMAN_APPROVAL"
    assert evaluate("TRANSFER_FUNDS", {}).decision == "DENY"
    assert evaluate("CHANGE_BANK_DETAILS", {}).decision == "DENY"


def test_close_requires_verification_and_voice_call_requires_consent_and_provider() -> None:
    assert evaluate("CLOSE_CASE", {}).reason_code == "VERIFICATION_PASS_REQUIRED"
    assert evaluate("CLOSE_CASE", {"verification_passed": True}).decision == "ALLOW"
    assert evaluate("OUTBOUND_PHONE_CALL", {}).reason_code == "CALL_CONSENT_REQUIRED"
    assert evaluate(
        "OUTBOUND_PHONE_CALL", {"consent": True, "provider_configured": False}
    ).reason_code == "CALL_PROVIDER_UNAVAILABLE"
    assert evaluate(
        "OUTBOUND_PHONE_CALL", {"consent": True, "provider_configured": True}
    ).decision == "ALLOW"


def test_unknown_action_is_denied() -> None:
    assert evaluate("RUN_ARBITRARY_SQL", {}).reason_code == "UNKNOWN_ACTION"
