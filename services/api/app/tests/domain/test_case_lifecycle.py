import inspect

import pytest

from app.db.models import SupportCase
from app.domain.case_lifecycle import CaseTransition, transition


def test_transition_signature_and_stub() -> None:
    sig = inspect.signature(transition)
    expected_params = ["case", "to_status", "expected_version", "actor"]
    assert list(sig.parameters.keys()) == expected_params
    assert sig.return_annotation is CaseTransition

    case = SupportCase(version=1, case_number="CAS-001", category="PAYOUT", summary="Test")
    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P2-C2"):
        transition(case, "INVESTIGATING", 1, "agent")
