"""Follow-up queue worker and runner.

Implements background polling and status evaluation using row-level locks
with `SELECT ... FOR UPDATE SKIP LOCKED` to prevent duplicate runs across
concurrent workers. Dispatches notifications only when a meaningful state
change has occurred.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redaction import redact
from app.db.models import (
    CaseEvent,
    Conversation,
    FollowupJob,
    Message,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    Transaction,
)


@dataclass
class FollowupResult:
    """Outcome of processing a follow-up job."""

    job_id: uuid.UUID
    case_id: uuid.UUID
    status: str
    meaningful_change: bool
    notification_sent: bool
    message: str
    details: dict[str, Any]


async def enqueue_followup_job(
    session: AsyncSession,
    case_id: uuid.UUID,
    run_at: datetime | None = None,
) -> FollowupJob:
    """Enqueue a new follow-up job for a support case."""
    now = datetime.now(UTC)
    scheduled_at = run_at or now

    job = FollowupJob(
        id=uuid.uuid4(),
        case_id=case_id,
        run_at=scheduled_at,
        status="PENDING",
        locked_at=None,
        attempts=0,
        created_at=now,
    )
    session.add(job)

    case_stmt = (
        update(SupportCase).where(SupportCase.id == case_id).values(followup_at=scheduled_at)
    )
    await session.execute(case_stmt)
    await session.commit()
    return job


async def claim_next_followup_job(
    session: AsyncSession,
    now: datetime | None = None,
    max_retries: int = 5,
) -> FollowupJob | None:
    """Claim next pending follow-up job using FOR UPDATE SKIP LOCKED.

    Atomically transitions the job to RUNNING status so no two workers
    claim the same job concurrently. If another worker claims the same candidate
    job first, retries with the next available pending job.
    """
    check_time = now or datetime.now(UTC)

    for _ in range(max_retries):
        stmt = (
            select(FollowupJob)
            .where(
                FollowupJob.status == "PENDING",
                FollowupJob.run_at <= check_time,
            )
            .order_by(FollowupJob.run_at.asc(), FollowupJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = (await session.execute(stmt)).scalar_one_or_none()
        if not job:
            return None

        # Atomic conditional update prevents races across SQLite and Postgres
        claim_stmt = (
            update(FollowupJob)
            .where(
                FollowupJob.id == job.id,
                FollowupJob.status == "PENDING",
            )
            .values(
                status="RUNNING",
                locked_at=check_time,
                attempts=FollowupJob.attempts + 1,
            )
        )
        result = await session.execute(claim_stmt)
        rowcount = getattr(result, "rowcount", 0)
        if rowcount > 0:
            await session.commit()
            refreshed = (
                await session.execute(select(FollowupJob).where(FollowupJob.id == job.id))
            ).scalar_one()
            return refreshed

        # If another worker already claimed this candidate job, rollback and retry
        await session.rollback()

    return None


async def process_followup_job(
    session: AsyncSession,
    job: FollowupJob,
    now: datetime | None = None,
) -> FollowupResult:
    """Execute status re-check for a claimed follow-up job.

    Notifies only on meaningful changes (e.g. discrepancy resolution, state change).
    If no change has occurred, logs an internal timeline audit and skips merchant notification.
    """
    check_time = now or datetime.now(UTC)

    case_stmt = select(SupportCase).where(SupportCase.id == job.case_id)
    case = (await session.execute(case_stmt)).scalar_one_or_none()

    if not case:
        job.status = "FAILED"
        job.locked_at = None
        await session.commit()
        return FollowupResult(
            job_id=job.id,
            case_id=job.case_id,
            status="FAILED",
            meaningful_change=False,
            notification_sent=False,
            message=f"Support case {job.case_id} not found.",
            details={"error": "NOT_FOUND"},
        )

    # If case is in a terminal state, complete job without notifying
    if case.status in {"RESOLVED", "REJECTED"}:
        job.status = "COMPLETED"
        job.locked_at = None
        case.followup_at = None
        await session.commit()
        return FollowupResult(
            job_id=job.id,
            case_id=case.id,
            status="COMPLETED",
            meaningful_change=False,
            notification_sent=False,
            message=f"Case is already in terminal state ({case.status}).",
            details={"case_status": case.status},
        )

    # Re-check financial records and current discrepancy
    batch_stmt = (
        select(SettlementBatch)
        .where(SettlementBatch.merchant_id == case.merchant_id)
        .order_by(SettlementBatch.created_at.desc())
    )
    batch = (await session.execute(batch_stmt)).scalar_one_or_none()

    current_discrepancy: Decimal | None = None
    if batch:
        tx_stmt = select(Transaction).where(
            Transaction.merchant_id == case.merchant_id,
            Transaction.status == "SUCCESS",
        )
        txns = list((await session.execute(tx_stmt)).scalars().all())
        expected_net = sum((tx.amount for tx in txns), Decimal("0.00"))

        entries_stmt = select(SettlementEntry).where(
            SettlementEntry.batch_id == batch.id,
            SettlementEntry.status == "SETTLED",
            SettlementEntry.entry_type == "CAPTURE",
        )
        entries = list((await session.execute(entries_stmt)).scalars().all())
        observed_net = sum((entry.amount for entry in entries), Decimal("0.00"))
        current_discrepancy = expected_net - observed_net

    # Fetch recent case events to check previous notifications
    events_stmt = (
        select(CaseEvent).where(CaseEvent.case_id == case.id).order_by(CaseEvent.created_at.desc())
    )
    events = list((await session.execute(events_stmt)).scalars().all())
    already_notified = any(e.event_type == "FOLLOWUP_STATUS_UPDATE" for e in events)

    meaningful_change = False
    change_summary = ""

    # Meaningful change 1: Discrepancy reached zero (settlement arrived)
    if current_discrepancy is not None and current_discrepancy == Decimal("0.00"):
        if not already_notified:
            meaningful_change = True
            batch_ref = batch.batch_ref if batch else "latest"
            change_summary = (
                f"Settlement discrepancy resolved to ₹0.00 for batch {batch_ref}. "
                "Verification is ready to finalize."
            )
    # Meaningful change 2: Case transitioned to VERIFYING or approved
    elif case.status == "VERIFYING":
        last_event = events[0] if events else None
        if (
            last_event
            and last_event.event_type in {"CASE_APPROVED", "SETTLEMENT_RESYNC_REQUESTED"}
            and not already_notified
        ):
            meaningful_change = True
            change_summary = (
                f"Settlement re-sync approved and processing for case {case.case_number}."
            )

    notification_sent = False
    if meaningful_change:
        event = CaseEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            actor="SYSTEM_FOLLOWUP_WORKER",
            event_type="FOLLOWUP_STATUS_UPDATE",
            from_status=case.status,
            to_status=case.status,
            visibility="MERCHANT",
            payload={
                "message": change_summary,
                "current_discrepancy": (
                    str(current_discrepancy) if current_discrepancy is not None else None
                ),
                "meaningful_change": True,
            },
            created_at=check_time,
        )
        session.add(event)

        # Notify active conversation in merchant's preferred language
        conv_stmt = (
            select(Conversation)
            .where(
                or_(
                    Conversation.active_case_id == case.id,
                    Conversation.merchant_id == case.merchant_id,
                )
            )
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        conv = (await session.execute(conv_stmt)).scalar_one_or_none()
        if conv:
            lang = conv.language.lower() if conv.language else "en"
            if lang == "hi":
                msg_content = f"केस {case.case_number} के लिए फॉलो-अप अपडेट: {change_summary}"
            elif lang == "mr":
                msg_content = f"केस {case.case_number} साठी फॉलो-अप अपडेट: {change_summary}"
            else:
                msg_content = f"Follow-up update for Case {case.case_number}: {change_summary}"

            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                role="ASSISTANT",
                content=redact(msg_content).clean_text,
                language=lang,
                created_at=check_time,
            )
            session.add(msg)
        notification_sent = True
    else:
        # Internal log without merchant disruption
        no_change_event = CaseEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            actor="SYSTEM_FOLLOWUP_WORKER",
            event_type="FOLLOWUP_CHECK_NO_CHANGE",
            from_status=case.status,
            to_status=case.status,
            visibility="INTERNAL",
            payload={
                "checked_at": check_time.isoformat(),
                "status": case.status,
                "current_discrepancy": (
                    str(current_discrepancy) if current_discrepancy is not None else None
                ),
                "meaningful_change": False,
            },
            created_at=check_time,
        )
        session.add(no_change_event)

    job.status = "COMPLETED"
    job.locked_at = None
    case.followup_at = None
    await session.commit()

    return FollowupResult(
        job_id=job.id,
        case_id=case.id,
        status="COMPLETED",
        meaningful_change=meaningful_change,
        notification_sent=notification_sent,
        message=(
            change_summary
            if meaningful_change
            else "Follow-up check completed: no meaningful status change detected."
        ),
        details={
            "case_status": case.status,
            "current_discrepancy": (
                str(current_discrepancy) if current_discrepancy is not None else None
            ),
            "meaningful_change": meaningful_change,
        },
    )


async def run_followup_for_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    now: datetime | None = None,
) -> FollowupResult:
    """Manually run follow-up check for a specific support case."""
    check_time = now or datetime.now(UTC)

    case_stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(case_stmt)).scalar_one_or_none()
    if not case:
        raise NotFoundError(f"Case {case_id} not found")

    job_stmt = (
        select(FollowupJob)
        .where(FollowupJob.case_id == case_id, FollowupJob.status == "PENDING")
        .order_by(FollowupJob.run_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = (await session.execute(job_stmt)).scalar_one_or_none()

    if job:
        job.status = "RUNNING"
        job.locked_at = check_time
        job.attempts += 1
        await session.commit()
    else:
        job = FollowupJob(
            id=uuid.uuid4(),
            case_id=case_id,
            run_at=check_time,
            status="RUNNING",
            locked_at=check_time,
            attempts=1,
            created_at=check_time,
        )
        session.add(job)
        await session.commit()

    return await process_followup_job(session=session, job=job, now=check_time)


async def run_followup_worker_once(
    session: AsyncSession,
    now: datetime | None = None,
) -> FollowupResult | None:
    """Single polling cycle for follow-up worker."""
    job = await claim_next_followup_job(session=session, now=now)
    if not job:
        return None
    return await process_followup_job(session=session, job=job, now=now)
