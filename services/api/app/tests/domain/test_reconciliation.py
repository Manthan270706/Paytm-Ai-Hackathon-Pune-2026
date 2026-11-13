from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.reconciliation import reconcile


def _capture(
    record_id: str = "capture-1",
    amount: Decimal = Decimal("15000.00"),
    status: str = "SUCCESS",
    provider_txn_id: str = "ptxn-1",
) -> dict[str, object]:
    return {
        "id": record_id,
        "amount": amount,
        "status": status,
        "provider_txn_id": provider_txn_id,
        "order_id": f"order-{record_id}",
        "source_type": "SYNTHETIC_DEMO",
    }


def _fee(amount: Decimal = Decimal("0.00")) -> dict[str, object]:
    return {
        "id": "fee-1",
        "amount": amount,
        "status": "DOCUMENTED",
        "source_type": "SYNTHETIC_DEMO",
    }


def _entry(amount: Decimal, provider_txn_id: str = "ptxn-1") -> dict[str, object]:
    return {
        "id": f"entry-{provider_txn_id}",
        "amount": amount,
        "status": "SETTLED",
        "provider_txn_id": provider_txn_id,
        "source_type": "SYNTHETIC_DEMO",
    }


def _reconcile(
    *,
    captures: list[dict[str, object]] | None = None,
    refunds: list[dict[str, object]] | None = None,
    fees: list[dict[str, object]] | None = None,
    taxes: list[dict[str, object]] | None = None,
    entries: list[dict[str, object]] | None = None,
    expected_date: date = date(2026, 11, 12),
    now: datetime = datetime(2026, 11, 13, tzinfo=UTC),
):
    return reconcile(
        captures=[] if captures is None else captures,
        refunds=[] if refunds is None else refunds,
        fees=[] if fees is None else fees,
        taxes=[] if taxes is None else taxes,
        entries=[] if entries is None else entries,
        expected_settlement_date=expected_date,
        now=now,
    )


def test_frozen_demo_scenario_is_overdue() -> None:
    result = _reconcile(
        captures=[_capture()],
        fees=[_fee()],
        entries=[_entry(Decimal("9000.00"))],
    )

    assert result.expected_net == Decimal("15000.00")
    assert result.observed == Decimal("9000.00")
    assert result.discrepancy == Decimal("6000.00")
    assert result.reason_code == "OVERDUE"
    assert result.source_ids == ["capture-1", "fee-1", "entry-ptxn-1"]
    assert result.trace["complete_evidence"] is True


def test_discrepancy_before_due_date_is_within_sla_pending() -> None:
    result = _reconcile(
        captures=[_capture()],
        fees=[_fee()],
        entries=[_entry(Decimal("9000.00"))],
        expected_date=date(2026, 11, 13),
    )

    assert result.reason_code == "WITHIN_SLA_PENDING"


def test_failed_payment_is_excluded_from_expected_net() -> None:
    result = _reconcile(
        captures=[_capture(), _capture("failed-1", Decimal("4000.00"), "FAILED", "ptxn-f")],
        fees=[_fee()],
        entries=[_entry(Decimal("15000.00"))],
    )

    assert result.expected_net == Decimal("15000.00")
    assert result.reason_code == "NO_DISCREPANCY"
    assert "failed-1" not in result.source_ids


def test_confirmed_refund_is_deducted_and_unconfirmed_refund_is_ignored() -> None:
    result = _reconcile(
        captures=[_capture()],
        refunds=[
            {
                "id": "refund-confirmed",
                "amount": Decimal("1000.00"),
                "status": "CONFIRMED",
                "source_type": "SYNTHETIC_DEMO",
            },
            {
                "id": "refund-pending",
                "amount": Decimal("500.00"),
                "status": "PENDING",
                "source_type": "SYNTHETIC_DEMO",
            },
        ],
        fees=[_fee()],
        entries=[_entry(Decimal("14000.00"))],
    )

    assert result.expected_net == Decimal("14000.00")
    assert result.reason_code == "NO_DISCREPANCY"
    assert "refund-confirmed" in result.source_ids
    assert "refund-pending" not in result.source_ids


def test_missing_fee_evidence_returns_insufficient_evidence() -> None:
    result = _reconcile(captures=[_capture()], entries=[_entry(Decimal("15000.00"))])

    assert result.reason_code == "INSUFFICIENT_EVIDENCE"
    assert result.trace["complete_evidence"] is False
    assert "Fee evidence is missing" in result.trace["issues"]


def test_successful_capture_without_entry_in_closed_batch_is_missing() -> None:
    result = _reconcile(captures=[_capture()], fees=[_fee()])

    assert result.reason_code == "MISSING"
    assert result.trace["missing_capture_ids"] == ["capture-1"]


def test_amount_only_entry_does_not_match_a_capture() -> None:
    result = _reconcile(
        captures=[_capture()],
        fees=[_fee()],
        entries=[
            {
                "id": "amount-lookalike",
                "amount": Decimal("15000.00"),
                "status": "SETTLED",
                "source_type": "SYNTHETIC_DEMO",
            }
        ],
    )

    assert result.observed == Decimal("0.00")
    assert result.reason_code == "MISSING"
    assert "amount-lookalike" not in result.source_ids


def test_float_money_is_rejected_as_insufficient_evidence() -> None:
    result = _reconcile(captures=[_capture(amount=15000.0)], fees=[_fee()])  # type: ignore[arg-type]

    assert result.reason_code == "INSUFFICIENT_EVIDENCE"
    assert isinstance(result.expected_net, Decimal)
    assert result.trace["complete_evidence"] is False


def test_zero_discrepancy_is_no_discrepancy() -> None:
    result = _reconcile(
        captures=[_capture()],
        fees=[_fee()],
        entries=[_entry(Decimal("15000.00"))],
    )

    assert result.reason_code == "NO_DISCREPANCY"
    assert result.discrepancy == Decimal("0.00")
