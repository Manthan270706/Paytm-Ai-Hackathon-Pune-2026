import inspect

import pytest

from app.db.models import Approval, SupportCase, User
from app.domain.approvals import validate_resume


def test_approvals_signature_and_stub() -> None:
    sig = inspect.signature(validate_resume)
    expected_params = ["approval", "case", "reviewer", "action"]
    assert list(sig.parameters.keys()) == expected_params

    appr = Approval(action="RESYNC", case_version=1, action_hash="hash")
    case = SupportCase(version=1, case_number="CAS-001", category="PAYOUT", summary="Test")
    user = User(email="agent@paytm.com", role="support")

    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P3-C1"):
        validate_resume(appr, case, user, "RESYNC")
