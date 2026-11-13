"""Independent, fresh-read verification for settlement case resolution."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models import (
    AuditEvent,
    CaseEvent,
    FeeRule,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    Transaction,
)

_ALLOWED_SOURCES = {"PAYTM_STAGING", "SYNTHETIC_DEMO"}
_SETTLED_STATUSES = {"SETTLED", "CONFIRMED", "SUCCESS", "SUCCESSFUL", "COMPLETED", "POSTED"}
_INACTIVE_ENTRY_STATUSES = {"PENDING", "PROCESSING", "FAILED", "CANCELLED", "CANCELED", "REVERSED"}


class VerificationResult(BaseModel):
    """Result of independent read-only resolution verification."""

    status: Literal["PASS", "FAIL"] = Field(
        description="Verification outcome: PASS if discrepancy eliminated, else FAIL"
    )
    before: Decimal = Field(description="Discrepancy amount before action")
    after: Decimal = Field(description="Discrepancy amount after action")
    evidence_timestamp: datetime = Field(
        description="Timestamp when verifier session observed the ground truth"
    )


def _money(value: Any, label: str) -> Decimal:
    if isinstance(value, (float, bool)) or value is None:
        raise ValidationError(f"{label} is missing or is not exact decimal evidence")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is not a valid decimal amount") from exc
    if not amount.is_finite():
        raise ValidationError(f"{label} is not a finite decimal amount")
    return amount


def _source_type(record: Any, label: str) -> str:
    source = getattr(record, "source_type", None)
    if source not in _ALLOWED_SOURCES:
        raise ValidationError(f"{label} has missing or unsupported provenance")
    return source


def _nested_evidence(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    candidates: list[Mapping[str, Any]] = [payload]
    for key in ("evidence", "reconciliation", "before_state"):
        child = payload.get(key)
        if isinstance(child, Mapping):
            candidates.append(child)
    return candidates


def _discrepancy_from_event(event: CaseEvent) -> Decimal | None:
    for payload in _nested_evidence(event.payload):
        for key in ("before_discrepancy", "discrepancy_before"):
            if key in payload:
                return _money(payload[key], "Recorded before discrepancy")
        if "expected_net" in payload and any(
            key in payload for key in ("observed", "observed_net", "before_observed")
        ):
            observed_key = next(
                key for key in ("before_observed", "observed", "observed_net") if key in payload
            )
            return _money(payload["expected_net"], "Recorded expected net") - _money(
                payload[observed_key], "Recorded before observed amount"
            )
        if "discrepancy" in payload:
            return _money(payload["discrepancy"], "Recorded before discrepancy")
    return None


def _batch_ref_from_event(event: CaseEvent) -> str | None:
    for payload in _nested_evidence(event.payload):
        value = payload.get("batch_ref")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def _recorded_before_state(
    verifier_session: AsyncSession,
    case_id: uuid.UUID,
    batch: SettlementBatch,
    expected_net: Decimal,
    events: list[CaseEvent],
) -> Decimal:
    for event in events:
        event_batch_ref = _batch_ref_from_event(event)
        if event_batch_ref is not None and event_batch_ref != batch.batch_ref:
            continue
        recorded_discrepancy = _discrepancy_from_event(event)
        if recorded_discrepancy is not None:
            return recorded_discrepancy

    resource = f"settlement_batches/{batch.id}"
    audit_stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.action == "SIMULATE_BANK_SETTLEMENT",
            AuditEvent.resource == resource,
        )
        .order_by(AuditEvent.created_at.desc())
    )
    audit_events = list((await verifier_session.execute(audit_stmt)).scalars().all())
    for audit in audit_events:
        payload = audit.payload or {}
        if not isinstance(payload, Mapping):
            continue
        if str(payload.get("merchant_id", "")) != str(batch.merchant_id):
            continue
        if payload.get("source_type") not in _ALLOWED_SOURCES:
            continue
        if "new_net" not in payload or "added_amount" not in payload:
            continue
        previous_observed = _money(payload["new_net"], "Recorded post-simulation net") - _money(
            payload["added_amount"], "Recorded simulated amount"
        )
        return expected_net - previous_observed

    raise ValidationError(
        "No recorded before-state is available for independent verification",
        details={"case_id": str(case_id), "batch_ref": batch.batch_ref},
    )


async def verify_resolution(
    case_id: uuid.UUID,
    rule: str,
    verifier_session: AsyncSession,
    now: datetime,
) -> VerificationResult:
    """Fetch settlement evidence afresh through the read-only verifier session.

    A recorded before-state is required from a case event or the audited demo
    settlement simulation. No ORM object or calculation result from the agent
    workflow is accepted as evidence.
    """
    if rule != "RECONCILE_DISCREPANCY_ZERO":
        raise ValidationError("Unsupported verification rule")

    # Refresh any ORM identities already present in this read-only session.
    case_stmt = (
        select(SupportCase)
        .where(SupportCase.id == case_id)
        .execution_options(populate_existing=True)
    )
    case = (await verifier_session.execute(case_stmt)).scalar_one_or_none()
    if case is None:
        raise NotFoundError("Case not found for verification")
    if str(case.status).upper() != "VERIFYING":
        raise ValidationError("Case must be in VERIFYING state before resolution checks")

    event_stmt = (
        select(CaseEvent)
        .where(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.created_at.desc())
        .execution_options(populate_existing=True)
    )
    events = list((await verifier_session.execute(event_stmt)).scalars().all())
    batch_ref = None
    for event in events:
        batch_ref = _batch_ref_from_event(event)
        if batch_ref:
            break

    batch_stmt = select(SettlementBatch).where(
        SettlementBatch.merchant_id == case.merchant_id
    ).execution_options(populate_existing=True)
    if batch_ref:
        batch_stmt = batch_stmt.where(SettlementBatch.batch_ref == batch_ref)
    batches = list((await verifier_session.execute(batch_stmt)).scalars().all())
    if len(batches) != 1:
        raise ValidationError(
            "Verification requires one unambiguous settlement batch",
            details={"case_id": str(case_id), "batch_ref": batch_ref},
        )
    batch = batches[0]
    if str(batch.status).upper() not in {"SETTLED", "CLOSED"}:
        raise ValidationError("Settlement batch is not closed for verification")

    start = datetime.combine(batch.date, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    captures_stmt = select(Transaction).where(
        Transaction.merchant_id == case.merchant_id,
        Transaction.status == "SUCCESS",
        Transaction.txn_time >= start,
        Transaction.txn_time < end,
    ).execution_options(populate_existing=True)
    captures = list((await verifier_session.execute(captures_stmt)).scalars().all())
    if not captures:
        raise ValidationError("No successful capture records are available for verification")
    for capture in captures:
        _source_type(capture, "Capture")

    fee_rules_stmt = select(FeeRule).where(
        FeeRule.merchant_id == case.merchant_id,
        FeeRule.active.is_(True),
    ).execution_options(populate_existing=True)
    fee_rules = list((await verifier_session.execute(fee_rules_stmt)).scalars().all())
    if not fee_rules:
        raise ValidationError("Documented fee rule is missing for verification")

    source_types = {_source_type(batch, "Settlement batch")}
    source_types.update(_source_type(fee_rule, "Fee rule") for fee_rule in fee_rules)
    source_types.update(_source_type(capture, "Capture") for capture in captures)
    capture_total = sum(
        (_money(capture.amount, "Capture amount") for capture in captures), Decimal("0")
    )
    fee_total = _money(batch.fees, "Documented batch fees")
    refund_total = _money(batch.refunds, "Documented batch refunds")
    expected_net = capture_total - fee_total - refund_total

    entries_stmt = (
        select(SettlementEntry)
        .where(SettlementEntry.batch_id == batch.id)
        .execution_options(populate_existing=True)
    )
    entries = list((await verifier_session.execute(entries_stmt)).scalars().all())
    capture_ids = {capture.id for capture in captures}
    settled_entries = []
    for entry in entries:
        entry_status = str(entry.status).upper()
        if entry_status in _SETTLED_STATUSES:
            capture_is_unmatched = (
                str(entry.entry_type).upper() == "CAPTURE"
                and entry.transaction_id not in capture_ids
            )
            if capture_is_unmatched:
                raise ValidationError(
                    "Settled capture entry does not match a successful transaction"
                )
            settled_entries.append(entry)
        elif entry_status not in _INACTIVE_ENTRY_STATUSES:
            raise ValidationError("Settlement entry has an unknown status")
    for entry in settled_entries:
        source_types.add(_source_type(entry, "Settlement entry"))
    if len(source_types) != 1:
        raise ValidationError("Financial sources cannot be silently mixed during verification")
    observed = sum(
        (_money(entry.amount, "Settlement entry amount") for entry in settled_entries), Decimal("0")
    )
    after = expected_net - observed
    before = await _recorded_before_state(
        verifier_session, case_id, batch, expected_net, events
    )

    return VerificationResult(
        status="PASS" if after == 0 else "FAIL",
        before=before,
        after=after,
        evidence_timestamp=now,
    )
