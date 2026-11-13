"""Deterministic, provenance-aware settlement reconciliation."""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field

_ZERO = Decimal("0.00")
_VALID_SOURCES = {"PAYTM_STAGING", "SYNTHETIC_DEMO"}
_SUCCESS_STATUSES = {"SUCCESS", "SUCCESSFUL", "CAPTURED", "SUCCEEDED"}
_CONFIRMED_STATUSES = {"CONFIRMED", "SUCCESS", "SUCCESSFUL", "SUCCEEDED"}
_SETTLED_STATUSES = {"SETTLED", "CONFIRMED", "SUCCESS", "SUCCESSFUL", "COMPLETED", "POSTED"}
_INACTIVE_ENTRY_STATUSES = {"PENDING", "PROCESSING", "FAILED", "CANCELLED", "CANCELED", "REVERSED"}


class ReconciliationResult(BaseModel):
    """Result of deterministic financial reconciliation."""

    expected_net: Decimal = Field(description="Sum of captures minus refunds, fees, taxes")
    observed: Decimal = Field(description="Sum of matched, settled entries")
    discrepancy: Decimal = Field(description="expected_net minus observed")
    reason_code: str = Field(
        description="NO_DISCREPANCY, WITHIN_SLA_PENDING, OVERDUE, MISSING, or INSUFFICIENT_EVIDENCE"
    )
    trace: dict[str, Any] = Field(default_factory=dict, description="Step-by-step arithmetic trace")
    source_ids: list[str] = Field(
        default_factory=list, description="IDs of source records used in computation"
    )


class _EvidenceError(ValueError):
    """An input record cannot safely be used as financial evidence."""


def _get(record: Any, *names: str) -> Any:
    for name in names:
        if isinstance(record, Mapping) and name in record:
            return record[name]
        if hasattr(record, name):
            return getattr(record, name)
    return None


def _decimal_amount(record: Any, label: str) -> Decimal:
    raw = _get(record, "amount", "amount_inr", "net_amount")
    if isinstance(raw, bool) or isinstance(raw, float) or raw is None:
        raise _EvidenceError(f"{label} has no valid Decimal-compatible amount")
    try:
        amount = raw if isinstance(raw, Decimal) else Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise _EvidenceError(f"{label} has an invalid amount") from exc
    if not amount.is_finite() or amount < 0:
        raise _EvidenceError(f"{label} amount must be finite and non-negative")
    return amount


def _record_id(record: Any) -> str | None:
    value = _get(record, "id", "source_id", "record_id")
    return str(value) if value is not None else None


def _source_type(record: Any, label: str) -> str:
    value = _get(record, "source_type")
    if value not in _VALID_SOURCES:
        raise _EvidenceError(f"{label} has missing or unsupported source_type")
    return value


def _references(record: Any) -> set[str]:
    values = (
        _get(record, "provider_txn_id", "provider_transaction_id", "transaction_id"),
        _get(record, "order_id", "order_ref"),
    )
    return {str(value).strip() for value in values if value is not None and str(value).strip()}


def _status(record: Any) -> str:
    value = _get(record, "status")
    return str(value).strip().upper() if value is not None else ""


def _include_deduction(record: Any, label: str, confirmed_only: bool) -> bool:
    status = _status(record)
    if confirmed_only:
        if status in _CONFIRMED_STATUSES:
            return True
        if status in {"PENDING", "PROCESSING", "FAILED", "CANCELLED", "CANCELED", "REJECTED"}:
            return False
        raise _EvidenceError(f"{label} has an unknown confirmation status")
    if status in {"DOCUMENTED", "CONFIRMED", "SUCCESS", "SUCCESSFUL", "ACTIVE", "APPLIED"}:
        return True
    if status in {"PENDING", "PROCESSING", "FAILED", "CANCELLED", "CANCELED", "REJECTED"}:
        return False
    raise _EvidenceError(f"{label} has an unknown documentation status")


def _is_before_or_on_due_date(expected_settlement_date: date, now: datetime) -> bool:
    return now.date() <= expected_settlement_date


def reconcile(
    captures: list[Any],
    refunds: list[Any],
    fees: list[Any],
    taxes: list[Any],
    entries: list[Any],
    expected_settlement_date: date,
    now: datetime,
) -> ReconciliationResult:
    """Calculate net settlement and classify it against the injected SLA clock.

    Input records may be mappings or typed objects. Each included amount must be
    Decimal-compatible (floats are rejected), and each used financial record must
    carry its source provenance. Settlement entries match captures only by a
    provider transaction ID or order ID.
    """
    trace: dict[str, Any] = {
        "currency": "INR",
        "expected_settlement_date": expected_settlement_date.isoformat(),
        "as_of": now.isoformat(),
        "components": {"captures": [], "refunds": [], "fees": [], "taxes": [], "entries": []},
        "issues": [],
    }
    source_ids: list[str] = []
    expected_net = _ZERO
    observed = _ZERO
    missing_capture_ids: list[str] = []
    incomplete = False

    if not captures:
        trace["issues"].append("No capture records were provided")
        incomplete = True

    successful_captures: list[tuple[Any, str, Decimal]] = []
    for capture in captures:
        status = _status(capture)
        if status in {"FAILED", "CANCELLED", "CANCELED", "DECLINED", "REVERSED"}:
            continue
        if status not in _SUCCESS_STATUSES:
            trace["issues"].append("Capture has missing or unsupported status")
            incomplete = True
            continue
        try:
            amount = _decimal_amount(capture, "Capture")
            source_type = _source_type(capture, "Capture")
            record_id = _record_id(capture)
            references = _references(capture)
            if not references:
                raise _EvidenceError("Successful capture has no transaction or order reference")
            if not record_id:
                raise _EvidenceError("Successful capture has no source ID")
        except _EvidenceError as exc:
            trace["issues"].append(str(exc))
            incomplete = True
            continue
        successful_captures.append((capture, record_id, amount))
        expected_net += amount
        source_ids.append(record_id)
        trace["components"]["captures"].append(
            {"id": record_id, "amount": str(amount), "source_type": source_type}
        )

    if not fees:
        trace["issues"].append("Fee evidence is missing")
        incomplete = True

    for label, key, records, confirmed_only in (
        ("refund", "refunds", refunds, True),
        ("fee", "fees", fees, False),
        ("tax", "taxes", taxes, False),
    ):
        for record in records:
            try:
                if not _include_deduction(record, label, confirmed_only):
                    continue
                amount = _decimal_amount(record, label.title())
                source_type = _source_type(record, label.title())
                record_id = _record_id(record)
                if not record_id:
                    raise _EvidenceError(f"{label.title()} has no source ID")
            except _EvidenceError as exc:
                trace["issues"].append(str(exc))
                incomplete = True
                continue
            expected_net -= amount
            source_ids.append(record_id)
            trace["components"][key].append(
                {"id": record_id, "amount": str(amount), "source_type": source_type}
            )

    capture_references: dict[str, str] = {}
    ambiguous_capture_references: set[str] = set()
    for capture, record_id, _ in successful_captures:
        for reference in _references(capture):
            if reference in capture_references and capture_references[reference] != record_id:
                ambiguous_capture_references.add(reference)
            else:
                capture_references[reference] = record_id
    matched_capture_ids: set[str] = set()
    matched_entry_ids: set[str] = set()
    for entry in entries:
        status = _status(entry)
        if status in _INACTIVE_ENTRY_STATUSES:
            continue
        if status not in _SETTLED_STATUSES:
            trace["issues"].append("Settlement entry has missing or unsupported status")
            incomplete = True
            continue
        try:
            amount = _decimal_amount(entry, "Settlement entry")
            source_type = _source_type(entry, "Settlement entry")
            entry_id = _record_id(entry)
            references = _references(entry)
            if not entry_id:
                raise _EvidenceError("Settlement entry has no source ID")
            if references & ambiguous_capture_references:
                raise _EvidenceError("Capture transaction or order reference is ambiguous")
            matching_capture_ids = {
                capture_references[ref] for ref in references if ref in capture_references
            }
            if len(matching_capture_ids) > 1:
                raise _EvidenceError("Settlement entry ambiguously matches multiple captures")
        except _EvidenceError as exc:
            trace["issues"].append(str(exc))
            incomplete = True
            continue
        if not matching_capture_ids:
            # An amount-only resemblance is deliberately not evidence of a match.
            continue
        if entry_id in matched_entry_ids:
            trace["issues"].append("Duplicate settlement entry source ID")
            incomplete = True
            continue
        matched_entry_ids.add(entry_id)
        matched_capture_ids.update(matching_capture_ids)
        observed += amount
        source_ids.append(entry_id)
        trace["components"]["entries"].append(
            {"id": entry_id, "amount": str(amount), "source_type": source_type}
        )

    missing_capture_ids = [
        record_id for _, record_id, _ in successful_captures if record_id not in matched_capture_ids
    ]
    discrepancy = expected_net - observed

    if incomplete:
        reason_code = "INSUFFICIENT_EVIDENCE"
    elif discrepancy == 0:
        reason_code = "NO_DISCREPANCY"
    elif discrepancy < 0:
        trace["issues"].append("Observed settlement exceeds expected net; human review is required")
        reason_code = "INSUFFICIENT_EVIDENCE"
    elif _is_before_or_on_due_date(expected_settlement_date, now):
        reason_code = "WITHIN_SLA_PENDING"
    elif missing_capture_ids:
        reason_code = "MISSING"
    else:
        reason_code = "OVERDUE"

    trace.update(
        {
            "expected_net": str(expected_net),
            "observed": str(observed),
            "discrepancy": str(discrepancy),
            "missing_capture_ids": missing_capture_ids,
            "complete_evidence": not incomplete,
            "matching_rule": "provider transaction ID or order ID; never amount alone",
            "arithmetic": (
                "expected_net = captures - confirmed_refunds - documented_fees "
                "- documented_taxes; discrepancy = expected_net - observed"
            ),
        }
    )
    return ReconciliationResult(
        expected_net=expected_net,
        observed=observed,
        discrepancy=discrepancy,
        reason_code=reason_code,
        trace=trace,
        source_ids=source_ids,
    )
