"""Tests for P4-A7 Follow-up Worker.

Verifies:
1. Two workers never run/claim the same job concurrently (SKIP LOCKED / atomic claim).
2. Status is re-checked and notifications are dispatched only on meaningful change.
3. Cases in terminal states do not produce redundant notifications.
4. Manual trigger endpoint POST /api/v1/cases/{id}/followup/run works with role enforcement.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CaseEvent,
    Conversation,
    Message,
    SupportCase,
)
from app.db.seed import MERCHANT_ID, reset_and_seed, simulate_bank_settlement
from app.main import app
from app.tests.conftest import shared_session_factory
from app.workers.followup import (
    claim_next_followup_job,
    enqueue_followup_job,
    process_followup_job,
)

pytestmark = pytest.mark.asyncio


async def create_test_case(
    session: AsyncSession,
    merchant_id: uuid.UUID | None = None,
    status: str = "AWAITING_APPROVAL",
    language: str = "en",
) -> SupportCase:
    """Helper to create a deterministic SupportCase and conversation for test runs."""
    now = datetime.now(UTC)
    case_id = uuid.uuid4()
    case = SupportCase(
        id=case_id,
        merchant_id=merchant_id or MERCHANT_ID,
        case_number=f"CAS-{now.strftime('%Y%m%d')}-{case_id.hex[:4].upper()}",
        category="SETTLEMENT_DELAY",
        priority="P1",
        status=status,
        queue="SETTLEMENT_OPS",
        summary="Missing ₹6,000 from settlement batch BATCH_20261112_01",
        idempotency_key=f"idem_{uuid.uuid4().hex}",
        version=1,
        created_at=now,
    )
    session.add(case)
    await session.flush()

    conv = Conversation(
        id=uuid.uuid4(),
        merchant_id=case.merchant_id,
        channel="CHAT",
        language=language,
        active_case_id=case.id,
        created_at=now,
    )
    session.add(conv)

    event = CaseEvent(
        id=uuid.uuid4(),
        case_id=case.id,
        actor="system",
        event_type="CASE_CREATED",
        from_status=None,
        to_status=status,
        visibility="MERCHANT",
        payload={"category": case.category, "summary": case.summary},
        created_at=now,
    )
    session.add(event)
    await session.commit()
    return case


async def test_concurrent_workers_never_claim_same_job() -> None:
    """Acceptance: two workers never run the same job."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        case = await create_test_case(session)

        # Enqueue exactly 1 pending job
        job = await enqueue_followup_job(session=session, case_id=case.id)
        job_id = job.id

    # Two concurrent worker sessions attempt to claim the job simultaneously
    async with shared_session_factory() as s1, shared_session_factory() as s2:
        claimed_1, claimed_2 = await asyncio.gather(
            claim_next_followup_job(session=s1),
            claim_next_followup_job(session=s2),
        )

        # Exactly one worker must have claimed the single pending job
        claimed_jobs = [j for j in (claimed_1, claimed_2) if j is not None]
        assert len(claimed_jobs) == 1, "Exactly one worker must claim the single job"
        assert claimed_jobs[0].id == job_id
        assert claimed_jobs[0].status == "RUNNING"

    # Now test with 2 distinct pending jobs: 2 workers must claim distinct jobs
    async with shared_session_factory() as session:
        await enqueue_followup_job(session=session, case_id=case.id)
        await enqueue_followup_job(session=session, case_id=case.id)

    async with shared_session_factory() as s1, shared_session_factory() as s2:
        claimed_a, claimed_b = await asyncio.gather(
            claim_next_followup_job(session=s1),
            claim_next_followup_job(session=s2),
        )

        assert claimed_a is not None, "Worker A must claim a job"
        assert claimed_b is not None, "Worker B must claim a job"
        assert claimed_a.id != claimed_b.id, "Two workers must never claim the same job"


async def test_followup_notifies_only_on_meaningful_change() -> None:
    """Verify worker re-checks status and notifies only on meaningful change."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        case = await create_test_case(session, status="AWAITING_APPROVAL", language="hi")

        # Enqueue follow-up job while discrepancy is still active (no external change)
        job1 = await enqueue_followup_job(session=session, case_id=case.id)

        # 1. First run: discrepancy is still ₹6,000, no meaningful progress
        result1 = await process_followup_job(session=session, job=job1)
        assert result1.status == "COMPLETED"
        assert result1.meaningful_change is False
        assert result1.notification_sent is False

        # Confirm internal event logged and NO merchant message created
        events_stmt = (
            select(CaseEvent)
            .where(
                CaseEvent.case_id == case.id,
                CaseEvent.event_type == "FOLLOWUP_CHECK_NO_CHANGE",
            )
        )
        no_change_events = list((await session.execute(events_stmt)).scalars().all())
        assert len(no_change_events) >= 1
        assert no_change_events[0].visibility == "INTERNAL"

        # 2. Simulate bank settlement credit: discrepancy resolved to ₹0.00
        await simulate_bank_settlement(session, merchant_id=case.merchant_id)

        # Enqueue new follow-up job now that funds have arrived
        job2 = await enqueue_followup_job(session=session, case_id=case.id)
        result2 = await process_followup_job(session=session, job=job2)

        # Meaningful change MUST be detected and notification dispatched
        assert result2.status == "COMPLETED"
        assert result2.meaningful_change is True
        assert result2.notification_sent is True
        assert "₹0.00" in result2.message

        # Verify merchant-visible CaseEvent exists
        update_events_stmt = (
            select(CaseEvent)
            .where(
                CaseEvent.case_id == case.id,
                CaseEvent.event_type == "FOLLOWUP_STATUS_UPDATE",
            )
        )
        update_events = list((await session.execute(update_events_stmt)).scalars().all())
        assert len(update_events) >= 1
        assert update_events[0].visibility == "MERCHANT"

        # Verify message was posted to merchant's conversation in Hindi
        msg_stmt = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.merchant_id == case.merchant_id)
            .order_by(Message.created_at.desc())
        )
        messages = list((await session.execute(msg_stmt)).scalars().all())
        assert len(messages) >= 1
        assert "₹0.00" in messages[0].content
        assert "फॉलो-अप अपडेट" in messages[0].content


async def test_followup_terminal_state_handling() -> None:
    """Verify follow-up completes cleanly without redundant notification on resolved case."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        case = await create_test_case(session, status="RESOLVED")

        job = await enqueue_followup_job(session=session, case_id=case.id)
        result = await process_followup_job(session=session, job=job)

        assert result.status == "COMPLETED"
        assert result.meaningful_change is False
        assert result.notification_sent is False
        assert "terminal state" in result.message


async def test_manual_trigger_api_route() -> None:
    """Acceptance: the manual trigger works with role-based access control."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        case = await create_test_case(session, status="AWAITING_APPROVAL")
        case_id = str(case.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Merchant role is forbidden (403)
        res_merchant = await client.post(
            f"/api/v1/cases/{case_id}/followup/run",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
        )
        assert res_merchant.status_code == 403

        # 2. Nonexistent case ID yields 404
        fake_id = str(uuid.uuid4())
        res_404 = await client.post(
            f"/api/v1/cases/{fake_id}/followup/run",
            headers={"Authorization": "Bearer demo-token-support_agent-1"},
        )
        assert res_404.status_code == 404

        # 3. Support role executes manual follow-up
        res_support = await client.post(
            f"/api/v1/cases/{case_id}/followup/run",
            headers={"Authorization": "Bearer demo-token-support_agent-1"},
        )
        assert res_support.status_code == 200
        data = res_support.json()["data"]
        assert data["case_id"] == case_id
        assert data["job_status"] == "COMPLETED"
        assert "meaningful_change" in data
        assert "notification_sent" in data
