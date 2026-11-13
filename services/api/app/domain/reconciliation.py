from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ReconciliationResult(BaseModel):
    """Result of deterministic financial reconciliation."""

    expected_net: Decimal = Field(description="Sum of captures minus refunds, fees, taxes")
    observed: Decimal = Field(description="Sum of observed settlement entries")
    discrepancy: Decimal = Field(description="expected_net minus observed")
    reason_code: str = Field(
        description="NO_DISCREPANCY, WITHIN_SLA_PENDING, OVERDUE, MISSING, or INSUFFICIENT_EVIDENCE"
    )
    trace: dict[str, Any] = Field(default_factory=dict, description="Step-by-step arithmetic trace")
    source_ids: list[str] = Field(
        default_factory=list, description="IDs of source records used in computation"
    )


def reconcile(
    captures: list[Any],
    refunds: list[Any],
    fees: list[Any],
    taxes: list[Any],
    entries: list[Any],
    expected_settlement_date: date,
    now: datetime,
) -> ReconciliationResult:
    """Reconcile captured transactions, deductions, and settlement entries.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C1.
    """
    raise NotImplementedError("TODO(core): Codex task P2-C1")
