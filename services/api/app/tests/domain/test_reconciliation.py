import inspect
from datetime import date, datetime

import pytest

from app.domain.reconciliation import ReconciliationResult, reconcile


def test_reconcile_signature_and_stub() -> None:
    sig = inspect.signature(reconcile)
    expected_params = [
        "captures",
        "refunds",
        "fees",
        "taxes",
        "entries",
        "expected_settlement_date",
        "now",
    ]
    assert list(sig.parameters.keys()) == expected_params
    assert sig.return_annotation is ReconciliationResult

    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P2-C1"):
        reconcile([], [], [], [], [], date.today(), datetime.now())
