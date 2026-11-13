import pytest

from app.core.exceptions import ConflictError, ForbiddenError
from app.db.models import SupportCase
from app.domain.case_lifecycle import CaseTransition, transition


def _case(status: str = "NEW", version: int = 1) -> SupportCase:
    return SupportCase(
        version=version,
        status=status,
        case_number="CAS-001",
        category="SETTLEMENT_MISMATCH",
        summary="Test settlement case",
        idempotency_key="case-create-001",
    )


def test_allowed_transition_mutates_status_version_and_emits_event() -> None:
    case = _case()

    result = transition(case, "TRIAGED", expected_version=1, actor="support-agent-1")

    assert isinstance(result, CaseTransition)
    assert result.new_status == "TRIAGED"
    assert result.new_version == 2
    assert case.status == "TRIAGED"
    assert case.version == 2
    assert result.event == {
        "event_type": "CASE_STATUS_CHANGED",
        "actor": "support-agent-1",
        "from_status": "NEW",
        "to_status": "TRIAGED",
        "version": 2,
    }


def test_stale_version_raises_conflict_without_mutating_case() -> None:
    case = _case(status="IN_PROGRESS", version=3)

    with pytest.raises(ConflictError):
        transition(case, "VERIFYING", expected_version=2, actor="agent")

    assert case.status == "IN_PROGRESS"
    assert case.version == 3


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("NEW", "IN_PROGRESS"),
        ("AWAITING_APPROVAL", "IN_PROGRESS"),
        ("RESOLVED", "IN_PROGRESS"),
        ("CANCELLED", "TRIAGED"),
    ],
)
def test_illegal_transition_is_forbidden(current: str, target: str) -> None:
    case = _case(status=current)

    with pytest.raises(ForbiddenError):
        transition(case, target, expected_version=1, actor="agent")

    assert case.status == current
    assert case.version == 1


def test_resolution_from_verifying_requires_recorded_pass() -> None:
    case = _case(status="VERIFYING")

    with pytest.raises(ForbiddenError, match="verification PASS"):
        transition(case, "RESOLVED", expected_version=1, actor="verifier")

    assert case.status == "VERIFYING"
    assert case.version == 1


def test_resolution_succeeds_after_verification_pass() -> None:
    case = _case(status="VERIFYING")
    case.verification_status = "PASS"

    result = transition(case, "RESOLVED", expected_version=1, actor="verifier")

    assert result.new_status == "RESOLVED"
    assert case.status == "RESOLVED"
    assert case.version == 2


def test_transition_requires_an_actor() -> None:
    case = _case()

    with pytest.raises(ForbiddenError, match="identified actor"):
        transition(case, "TRIAGED", expected_version=1, actor=" ")
