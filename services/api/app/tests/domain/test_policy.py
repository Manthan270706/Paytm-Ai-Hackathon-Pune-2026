import inspect

import pytest

from app.domain.policy import PolicyDecision, evaluate


def test_policy_signature_and_stub() -> None:
    sig = inspect.signature(evaluate)
    assert list(sig.parameters.keys()) == ["action", "context"]
    assert sig.return_annotation is PolicyDecision

    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P2-C2"):
        evaluate("SETTLEMENT_RESYNC", {"amount": 6000})
