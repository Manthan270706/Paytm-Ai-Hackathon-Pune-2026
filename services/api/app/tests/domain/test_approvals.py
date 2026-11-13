import json
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import ConflictError, ForbiddenError
from app.db.models import Approval, SupportCase, User
from app.domain.approvals import compute_action_hash, validate_resume
from app.domain.policy import PolicyDecision


def _case(version: int = 3) -> SupportCase:
    return SupportCase(
        version=version,
        status="AWAITING_APPROVAL",
        case_number="CAS-001",
        category="SETTLEMENT_MISMATCH",
        summary="Approved settlement re-sync",
        idempotency_key="case-001",
    )


def _payload(discrepancy: str = "6000.00") -> dict[str, Any]:
    return {"action_type": "SETTLEMENT_RESYNC", "parameters": {"discrepancy": discrepancy}}


def _approval(
    *,
    version: int = 3,
    payload: dict[str, Any] | None = None,
    decision: str = "PENDING",
) -> Approval:
    action_payload = _payload() if payload is None else payload
    action_type = action_payload["action_type"]
    parameters = action_payload["parameters"]
    return Approval(
        action="SETTLEMENT_RESYNC",
        case_version=version,
        action_hash=compute_action_hash(action_type, parameters),
        decision=decision,
        status="ACTIVE",
    )


def _action(payload: dict[str, Any] | None = None) -> str:
    return json.dumps(_payload() if payload is None else payload)


def _reviewer(role: str = "SUPPORT_AGENT") -> User:
    return User(email="reviewer@paytm.demo", role=role, is_active=True)


def test_validate_resume_signature_and_approved_action() -> None:
    result = validate_resume(_approval(), _case(), _reviewer(), _action())

    assert result is None


def test_merchant_cannot_resume_approval() -> None:
    with pytest.raises(ForbiddenError, match="Reviewer role"):
        validate_resume(_approval(), _case(), _reviewer("MERCHANT"), _action())


def test_inactive_reviewer_cannot_resume_approval() -> None:
    reviewer = _reviewer()
    reviewer.is_active = False

    with pytest.raises(ForbiddenError, match="Inactive"):
        validate_resume(_approval(), _case(), reviewer, _action())


def test_changed_case_version_returns_conflict() -> None:
    with pytest.raises(ConflictError, match="case version changed"):
        validate_resume(_approval(version=2), _case(version=3), _reviewer(), _action())


def test_changed_action_parameters_return_conflict() -> None:
    approval = _approval(payload=_payload("6000.00"))

    with pytest.raises(ConflictError, match="action parameters changed"):
        validate_resume(approval, _case(), _reviewer(), _action(_payload("7000.00")))


def test_changed_action_type_returns_conflict() -> None:
    payload = {"action_type": "TRANSFER_FUNDS", "parameters": {}}
    with pytest.raises(ConflictError, match="action type changed"):
        validate_resume(_approval(), _case(), _reviewer(), _action(payload))


def test_current_policy_deny_returns_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.domain.approvals.evaluate",
        lambda _action, _context: PolicyDecision(
            decision="DENY", reason_code="POLICY_CHANGED_TO_DENY"
        ),
    )

    with pytest.raises(ForbiddenError, match="Current policy denies"):
        validate_resume(_approval(), _case(), _reviewer(), _action())


def test_rejected_approval_cannot_resume() -> None:
    with pytest.raises(ForbiddenError, match="Rejected or inactive"):
        validate_resume(
            _approval(decision="REJECTED"), _case(), _reviewer(), _action()
        )


def test_decimal_action_parameters_have_stable_hashes() -> None:
    first = compute_action_hash(" settlement_resync ", {"discrepancy": Decimal("6000.00")})
    second = compute_action_hash("SETTLEMENT_RESYNC", {"discrepancy": "6000.00"})

    assert first == second
