"""Regression tests for Codex audit findings (P5-A3).

1. cases.py verify: reject with CONFLICT unless the case status is VERIFYING.
2. webhooks.py: always call validate_paytm_checksum. Any demo bypass only when
   DEMO_DATA_MODE=true, and the stored row is labelled SYNTHETIC_DEMO, never PAYTM_STAGING.
3. demo.py: simulate-settlement and reset require support role AND DEMO_DATA_MODE=true;
   audit each call.
4. transactions.py: unknown transaction ID returns 404 NOT_FOUND (no synthetic SUCCESS fallback).
5. agents/runner.py: use core.redaction.redact for stored messages; remove narrower helper.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.redaction import redact
from app.db.models import AuditEvent, Conversation, Message, SupportCase
from app.db.seed import MERCHANT_ID, reset_and_seed
from app.main import app
from app.tests.conftest import shared_session_factory

client = TestClient(app)
MERCHANT_TOKEN = {"Authorization": "Bearer demo-token-merchant-1"}
SUPPORT_TOKEN = {"Authorization": "Bearer demo-token-support_agent-1"}
SUPERVISOR_TOKEN = {"Authorization": "Bearer demo-token-supervisor-1"}


@pytest.mark.asyncio
async def test_regression_1_verify_rejects_with_conflict_unless_verifying() -> None:
    """1. cases.py verify: reject with CONFLICT (409) unless case status is VERIFYING."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        case_id = uuid.uuid4()
        case = SupportCase(
            id=case_id,
            merchant_id=MERCHANT_ID,
            case_number=f"CAS-{uuid.uuid4().hex[:6].upper()}",
            category="SETTLEMENT_MISMATCH",
            priority="P2",
            status="AWAITING_APPROVAL",
            queue="SETTLEMENT_OPS",
            summary="Testing verify conflict rejection",
            idempotency_key=f"IDEMP-{uuid.uuid4().hex}",
            version=1,
        )
        session.add(case)
        await session.commit()

    # Attempt to verify while status is AWAITING_APPROVAL -> must reject with 409 CONFLICT
    res = client.post(f"/api/v1/cases/{case_id}/verify", headers=SUPPORT_TOKEN)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"
    assert "VERIFYING" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_regression_2_webhook_demo_bypass_synthetic_demo_and_validation() -> None:
    """2. webhooks.py: always calls validate_paytm_checksum. Demo bypass only when

    DEMO_DATA_MODE=true and labelled SYNTHETIC_DEMO, never PAYTM_STAGING.
    """
    from app.tests.conftest import generate_test_paytm_checksum

    event_id = f"EVT-REGRESSION-{uuid.uuid4().hex[:8]}"
    params = {
        "event_id": event_id,
        "provider_txn_id": "TXN_MOCK_1",
        "order_id": "ORD_MOCK_1",
        "amount": "6000.00",
        "status": "SUCCESS",
    }
    valid_checksum = generate_test_paytm_checksum(params)
    payload = {
        **params,
        "CHECKSUMHASH": valid_checksum,
    }

    # When DEMO_DATA_MODE=True: demo fallback validates with demo key and labels SYNTHETIC_DEMO
    original_demo_mode = settings.DEMO_DATA_MODE
    original_key = settings.PAYTM_MERCHANT_KEY
    try:
        settings.DEMO_DATA_MODE = True
        settings.PAYTM_MERCHANT_KEY = ""
        res = client.post("/api/v1/webhooks/paytm", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["meta"]["source_type"] == "SYNTHETIC_DEMO"
        assert body["data"]["received"] is True

        # Check stored AuditEvent has source_type SYNTHETIC_DEMO
        async with shared_session_factory() as session:
            stmt = select(AuditEvent).where(AuditEvent.resource == f"webhook_events/{event_id}")
            audit_entry = (await session.execute(stmt)).scalar_one_or_none()
            assert audit_entry is not None
            assert audit_entry.payload["source_type"] == "SYNTHETIC_DEMO"
            assert audit_entry.payload["demo_bypass"] is True

        # While DEMO_DATA_MODE=True, hardcoded mock or invalid demo signatures
        # must be rejected with 400
        for bad_sig in [
            "mock_checksum_abc123",
            "demo_valid_signature",
            "demo_invalid",
            "demo_invalid_signature",
            "demo_tampered",
            "tampered_signature_xyz",
        ]:
            res_bad = client.post(
                "/api/v1/webhooks/paytm",
                json={
                    **params,
                    "event_id": f"EVT-REGRESSION-{uuid.uuid4().hex[:8]}",
                    "checksum": bad_sig,
                },
            )
            assert res_bad.status_code == 400
            assert "signature verification failed" in res_bad.json()["detail"].lower()

        # When DEMO_DATA_MODE=False and merchant key is empty: validation fails with 400
        settings.DEMO_DATA_MODE = False
        res_fail = client.post(
            "/api/v1/webhooks/paytm",
            json={
                **params,
                "event_id": f"EVT-REGRESSION-{uuid.uuid4().hex[:8]}",
                "checksum": valid_checksum,
            },
        )
        assert res_fail.status_code == 400
    finally:
        settings.DEMO_DATA_MODE = original_demo_mode
        settings.PAYTM_MERCHANT_KEY = original_key


@pytest.mark.asyncio
async def test_regression_3_demo_endpoints_require_support_and_demo_mode_and_audit() -> None:
    """3. demo.py: simulate-settlement and reset require support role AND DEMO_DATA_MODE=true;

    audit each call.
    """
    original_demo_mode = settings.DEMO_DATA_MODE
    try:
        settings.DEMO_DATA_MODE = True

        # Unauthenticated calls reject with 401
        assert client.post("/api/v1/demo/reset").status_code == 401
        assert client.post("/api/v1/demo/simulate-settlement", json={}).status_code == 401

        # Merchant role calls reject with 403
        assert client.post("/api/v1/demo/reset", headers=MERCHANT_TOKEN).status_code == 403
        assert (
            client.post(
                "/api/v1/demo/simulate-settlement", headers=MERCHANT_TOKEN, json={}
            ).status_code
            == 403
        )

        # When DEMO_DATA_MODE=False, even support role rejects with 403
        settings.DEMO_DATA_MODE = False
        assert client.post("/api/v1/demo/reset", headers=SUPPORT_TOKEN).status_code == 403
        assert (
            client.post(
                "/api/v1/demo/simulate-settlement", headers=SUPPORT_TOKEN, json={}
            ).status_code
            == 403
        )

        # Support role succeeds when DEMO_DATA_MODE=True and records AuditEvents
        settings.DEMO_DATA_MODE = True
        reset_res = client.post("/api/v1/demo/reset", headers=SUPPORT_TOKEN)
        assert reset_res.status_code == 200

        sim_res = client.post(
            "/api/v1/demo/simulate-settlement",
            headers=SUPPORT_TOKEN,
            json={"amount": "6000.00", "batch_ref": "BATCH_20261112_01"},
        )
        assert sim_res.status_code == 200

        async with shared_session_factory() as session:
            stmt_reset = (
                select(AuditEvent)
                .where(AuditEvent.action == "DEMO_RESET")
                .order_by(AuditEvent.created_at.desc())
            )
            audit_reset = (await session.execute(stmt_reset)).scalars().first()
            assert audit_reset is not None
            assert "support" in audit_reset.actor

            stmt_sim = (
                select(AuditEvent)
                .where(AuditEvent.action == "DEMO_SIMULATE_SETTLEMENT")
                .order_by(AuditEvent.created_at.desc())
            )
            audit_sim = (await session.execute(stmt_sim)).scalars().first()
            assert audit_sim is not None
            assert "support" in audit_sim.actor
    finally:
        settings.DEMO_DATA_MODE = original_demo_mode


@pytest.mark.asyncio
async def test_regression_4_unknown_transaction_returns_404_no_synthetic_fallback() -> None:
    """4. transactions.py: unknown transaction ID returns 404 NOT_FOUND.

    No synthetic SUCCESS fallback anywhere.
    """
    random_txn_id = uuid.uuid4()
    res = client.get(f"/api/v1/transactions/{random_txn_id}", headers=MERCHANT_TOKEN)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_regression_5_agents_runner_uses_core_redaction_for_stored_messages() -> None:
    """5. agents/runner.py: use core.redaction.redact for stored messages;

    remove the narrower helper.
    """
    from app.agents.runner import run_agent_turn

    secrets = "My UPI PIN is 4821 and CVV is 987 and account number is 123456789012"
    expected_clean = redact(secrets).clean_text

    async with shared_session_factory() as session:
        await reset_and_seed(session)
        agent_run, result = await run_agent_turn(
            merchant_id=MERCHANT_ID,
            message=secrets,
            session=session,
        )
        # Verify Message row in DB has clean_text from core.redaction.redact
        msg = (
            await session.execute(
                select(Message).where(
                    Message.conversation_id == agent_run.conversation_id,
                    Message.role == "USER",
                )
            )
        ).scalar_one()

        assert msg.content == expected_clean
        assert "4821" not in msg.content
        assert "987" not in msg.content
        assert "123456789012" not in msg.content
        assert "[REDACTED_PIN]" in msg.content
        assert "[REDACTED_CVV]" in msg.content
        assert "[REDACTED_ACCOUNT]" in msg.content

        # Verify ASSISTANT Message row in DB has also passed through core.redaction.redact
        assistant_msg = (
            await session.execute(
                select(Message).where(
                    Message.conversation_id == agent_run.conversation_id,
                    Message.role == "ASSISTANT",
                )
            )
        ).scalar_one()
        assert assistant_msg.content == redact(assistant_msg.content).clean_text


@pytest.mark.asyncio
async def test_regression_5_voice_disclosure_stored_with_core_redaction() -> None:
    """Voice session disclosure messages are stored using core.redaction.redact."""
    res = client.post(
        "/api/v1/voice/sessions",
        json={"language": "en"},
        headers=MERCHANT_TOKEN,
    )
    assert res.status_code == 200
    conv_id = uuid.UUID(res.json()["data"]["conversation_id"])

    async with shared_session_factory() as session:
        disclosure_msg = (
            await session.execute(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.role == "SYSTEM",
                )
            )
        ).scalar_one()
        assert (
            disclosure_msg.content
            == redact(
                "AI-identity disclosed: OpsSaathi AI operations teammate (voice session)"
            ).clean_text
        )


@pytest.mark.asyncio
async def test_regression_5_followup_worker_messages_stored_with_core_redaction() -> None:
    """Follow-up worker messages are stored using core.redaction.redact."""
    from app.db.seed import simulate_bank_settlement
    from app.workers.followup import enqueue_followup_job, process_followup_job

    async with shared_session_factory() as session:
        await reset_and_seed(session)
        now = datetime.now(UTC)
        case_id = uuid.uuid4()
        case = SupportCase(
            id=case_id,
            merchant_id=MERCHANT_ID,
            case_number=f"CAS-{now.strftime('%Y%m%d')}-{case_id.hex[:4].upper()}",
            category="SETTLEMENT_DELAY",
            priority="P1",
            status="AWAITING_APPROVAL",
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
            language="en",
            active_case_id=case.id,
            created_at=now,
        )
        session.add(conv)
        await session.flush()

        # Simulate settlement to resolve discrepancy and trigger meaningful change
        await simulate_bank_settlement(session, merchant_id=case.merchant_id)

        job = await enqueue_followup_job(session=session, case_id=case.id)
        res = await process_followup_job(session=session, job=job)
        assert res.meaningful_change is True
        assert res.notification_sent is True

        msgs = (
            (
                await session.execute(
                    select(Message).where(
                        Message.conversation_id == conv.id,
                        Message.role == "ASSISTANT",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(msgs) >= 1
        for m in msgs:
            assert m.content == redact(m.content).clean_text
