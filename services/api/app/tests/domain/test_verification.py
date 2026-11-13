import inspect
import uuid
from datetime import datetime

import pytest

from app.domain.verification import VerificationResult, verify_resolution


@pytest.mark.asyncio
async def test_verification_signature_and_stub() -> None:
    sig = inspect.signature(verify_resolution)
    expected_params = ["case_id", "rule", "verifier_session", "now"]
    assert list(sig.parameters.keys()) == expected_params
    assert sig.return_annotation is VerificationResult

    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P3-C2"):
        await verify_resolution(uuid.uuid4(), "RECONCILE_DISCREPANCY_ZERO", None, datetime.now())  # type: ignore[arg-type]
