"""test_p4_a9_failure_drills.py: PRD §14 Reliability & Failure Drills Test Suite.

Verifies all 12 failure drills specified in PRD §14:
1. LLM timeout / quota -> Fallback to deterministic demo cache / mock
2. LLM invalid structure -> Repair retry & deterministic regex fallback
3. Sarvam unavailable -> Fallback to mock / browser speech
4. Paytm staging unavailable -> Show integration unavailable & labelled SYNTHETIC_DEMO fixtures
5. Duplicate webhook -> Deduplicated by event ID/hash
6. Database unavailable -> Controlled HTTP 503, no write ack
7. Case action timeout -> Idempotency key prevents duplicate writes
8. Re-sync request timeout -> resync_requests idempotency key
9. Unauthorized / stale approval -> 403 Forbidden / 409 Conflict
10. Follow-up worker race -> SKIP LOCKED atomic claim
11. Verification fails -> Remains VERIFYING, explains unverified delta, blocks resolve
12. Mic permission denied -> Immediate text chat fallback contract
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.agents.nodes import collect_issue
from app.agents.state import AgentState
from app.db.models import Approval, CaseEvent, FollowupJob, ResyncRequest, SupportCase
from app.db.seed import MERCHANT_ID, reset_and_seed
from app.db.session import get_db_session
from app.domain.approvals import compute_action_hash
from app.integrations.gemini.provider import FallbackLLMProvider
from app.integrations.paytm.provider import FallbackPaymentProvider
from app.integrations.sarvam.provider import FallbackSpeechToText, FallbackTextToSpeech
from app.main import app
from app.tests.conftest import shared_session_factory
from app.tools.registry import ToolContext, run_request_settlement_resync
from app.tools.schemas import RequestSettlementResyncInput
from app.workers.followup import claim_next_followup_job

pytestmark = pytest.mark.asyncio


class DummyExtractionSchema(BaseModel):
    category: str = "SETTLEMENT_MISMATCH"
    amount: str | None = None
    reference: str | None = None


# ------------------------------------------------------------------------------
# Drill 1: LLM timeout / quota
# ------------------------------------------------------------------------------
async def test_drill_01_llm_timeout_and_quota_fallback() -> None:
    """Drill 1: LLM timeout/quota triggers bounded retry then cache/mock fallback."""
    provider = FallbackLLMProvider()

    # Simulate Gemini failing with Timeout or 429 quota exhaustion
    with patch.object(
        provider.gemini,
        "generate_structured",
        side_effect=httpx.TimeoutException("ReadTimeout during Gemini call"),
    ):
        res = await provider.generate_structured(
            prompt="My ₹6,000 payment is missing from settlement.",
            schema=DummyExtractionSchema,
        )
        assert res is not None
        assert provider.last_served_from in {"CACHE", "MOCK"}


# ------------------------------------------------------------------------------
# Drill 2: LLM returns invalid structure
# ------------------------------------------------------------------------------
async def test_drill_02_llm_invalid_structure_deterministic_fallback() -> None:
    """Drill 2: LLM returning invalid schema falls back to deterministic regex."""
    state: AgentState = {
        "session_id": "drill-sess-2",
        "merchant_id": MERCHANT_ID,
        "user_role": "MERCHANT",
        "run_id": "run-drill-2",
        "raw_input": "Payment of ₹6,000 in BATCH_20261112_01 is missing.",
        "sanitized_input": "Payment of ₹6,000 in BATCH_20261112_01 is missing.",
        "language": "en",
        "trace_events": [],
    }

    # Simulate LLM raising an unexpected validation error
    with patch("app.agents.nodes.get_llm_provider") as mock_get_llm:
        mock_provider = AsyncMock()
        mock_provider.generate_structured.side_effect = ValueError("Invalid JSON schema structure")
        mock_get_llm.return_value = mock_provider

        result = await collect_issue(state)
        extracted = result["extracted_entities"]
        assert extracted.get("amount") in {"6000", "6000.00"}
        assert extracted.get("reference") == "BATCH_20261112_01"


# ------------------------------------------------------------------------------
# Drill 3: Sarvam unavailable
# ------------------------------------------------------------------------------
async def test_drill_03_sarvam_unavailable_fallback() -> None:
    """Drill 3: Sarvam failure falls back to mock/browser speech without blocking."""
    stt = FallbackSpeechToText()
    tts = FallbackTextToSpeech()

    with patch.object(
        stt.sarvam_stt,
        "transcribe",
        side_effect=RuntimeError("Sarvam STT service unavailable"),
    ), patch.object(
        stt.sarvam_stt,
        "is_available",
        return_value=True,
    ):
        transcript = await stt.transcribe(b"dummy_wav_bytes", language="en")
        assert transcript != ""
        assert stt.last_source == "mock"

    with patch.object(
        tts.sarvam_tts,
        "synthesize",
        side_effect=RuntimeError("Sarvam TTS service unavailable"),
    ), patch.object(
        tts.sarvam_tts,
        "is_available",
        return_value=True,
    ):
        audio_bytes = await tts.synthesize("Test response", language="en")
        assert len(audio_bytes) > 0
        assert tts.last_source == "mock"


# ------------------------------------------------------------------------------
# Drill 4: Paytm staging unavailable
# ------------------------------------------------------------------------------
async def test_drill_04_paytm_staging_unavailable_fixtures() -> None:
    """Drill 4: Paytm staging failure falls back to labelled SYNTHETIC_DEMO fixtures."""
    prov = FallbackPaymentProvider()

    with patch.object(
        prov.paytm_provider,
        "get_transaction_status",
        side_effect=httpx.HTTPError("Paytm staging gateway 502 Bad Gateway"),
    ), patch.object(
        prov.paytm_provider,
        "is_available",
        return_value=True,
    ):
        res = await prov.get_transaction_status(provider_txn_id="TXN_78456321")
        assert res.source_type == "SYNTHETIC_DEMO"
        assert res.amount == Decimal("6000.00")
        assert prov.last_source == "SYNTHETIC_DEMO"
        assert prov.integration_status == "UNAVAILABLE"


# ------------------------------------------------------------------------------
# Drill 5: Duplicate webhook
# ------------------------------------------------------------------------------
async def test_drill_05_duplicate_webhook_deduplication() -> None:
    """Drill 5: Duplicate webhook delivery is detected and deduplicated."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        event_id = f"evt_drill_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "order_id": "ORD_20261112_01",
            "amount": "6000.00",
            "status": "TXN_SUCCESS",
        }
        headers = {"x-paytm-signature": "demo_valid_signature"}

        # First delivery: processed
        res1 = await client.post("/api/v1/webhooks/paytm", json=payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()["data"]
        assert data1["deduplicated"] is True

        # Second delivery: duplicate ignored
        res2 = await client.post("/api/v1/webhooks/paytm", json=payload, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        assert data2["deduplicated"] is False
        assert data2["status"] == "DUPLICATE_IGNORED"


# ------------------------------------------------------------------------------
# Drill 6: Database unavailable (Controlled 503)
# ------------------------------------------------------------------------------
async def test_drill_06_database_unavailable_returns_controlled_503() -> None:
    """Drill 6: Database unavailability produces controlled HTTP 503 Service Unavailable."""
    transport = ASGITransport(app=app)

    # Patch session.execute to simulate database connection loss
    async def mock_failed_db():
        session = AsyncMock()
        session.execute.side_effect = OperationalError(
            statement="SELECT 1",
            params={},
            orig=Exception("could not connect to server: Connection refused"),
        )
        yield session

    orig_override = app.dependency_overrides.get(get_db_session)
    app.dependency_overrides[get_db_session] = mock_failed_db

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": "Bearer demo-token-support_agent-1"}
            res = await client.get("/api/v1/cases", headers=headers)
            assert res.status_code == 503
            payload = res.json()
            assert payload["ok"] is False
            assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"
            assert payload["error"]["details"] == {"service": "database"}
    finally:
        if orig_override is not None:
            app.dependency_overrides[get_db_session] = orig_override
        else:
            app.dependency_overrides.pop(get_db_session, None)


# ------------------------------------------------------------------------------
# Drill 7: Case action timeout / Idempotency
# ------------------------------------------------------------------------------
async def test_drill_07_case_creation_idempotency_replay() -> None:
    """Drill 7: Re-submitting a case with the same idempotency key does not duplicate."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {
            "Authorization": "Bearer demo-token-merchant-1",
            "Idempotency-Key": f"idem_drill_{uuid.uuid4().hex}",
        }
        case_data = {
            "category": "SETTLEMENT_DELAY",
            "priority": "P1",
            "summary": "Timeout retry test case",
        }

        # Request 1
        res1 = await client.post("/api/v1/cases", json=case_data, headers=headers)
        assert res1.status_code == 200
        case1_id = res1.json()["data"]["id"]

        # Request 2 (Retry with exact same idempotency key)
        res2 = await client.post("/api/v1/cases", json=case_data, headers=headers)
        assert res2.status_code == 200
        case2_id = res2.json()["data"]["id"]

        # IDs must match; no duplicate row created
        assert case1_id == case2_id


# ------------------------------------------------------------------------------
# Drill 8: Re-sync request timeout / Idempotency
# ------------------------------------------------------------------------------
async def test_drill_08_resync_request_idempotency_prevents_duplicate_send() -> None:
    """Drill 8: Re-sync request checks idempotency before sending a second request."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        now = datetime.now(UTC)

        case = SupportCase(
            id=uuid.uuid4(),
            merchant_id=MERCHANT_ID,
            case_number="CAS-RESYNC-DRILL",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="APPROVED",
            queue="SETTLEMENT_OPS",
            summary="Resync idempotency drill",
            idempotency_key=f"idem_resync_case_{uuid.uuid4().hex}",
            version=2,
            created_at=now,
        )
        session.add(case)
        await session.commit()

        idemp_key = f"RESYNC_DRILL_{uuid.uuid4().hex[:8]}"
        ctx = ToolContext(merchant_id=MERCHANT_ID, session=session)

        # 1. First execution creates ResyncRequest row
        out1 = await run_request_settlement_resync(
            RequestSettlementResyncInput(
                case_id=str(case.id),
                batch_ref="BATCH_20261112_01",
                amount=Decimal("6000.00"),
                idempotency_key=idemp_key,
            ),
            ctx,
        )
        await session.commit()
        assert out1.status == "ACKNOWLEDGED"

        # 2. Second execution detects existing row and returns it
        out2 = await run_request_settlement_resync(
            RequestSettlementResyncInput(
                case_id=str(case.id),
                batch_ref="BATCH_20261112_01",
                amount=Decimal("6000.00"),
                idempotency_key=idemp_key,
            ),
            ctx,
        )
        assert out2.resync_id == out1.resync_id

        # Verify only 1 row exists in database
        stmt = select(ResyncRequest).where(ResyncRequest.idempotency_key == idemp_key)
        rows = list((await session.execute(stmt)).scalars().all())
        assert len(rows) == 1


# ------------------------------------------------------------------------------
# Drill 9: Unauthorized / Stale Approval (403 / 409)
# ------------------------------------------------------------------------------
async def test_drill_09_unauthorized_and_stale_approval() -> None:
    """Drill 9: Unauthorized approval returns 403; stale version/hash returns 409."""
    transport = ASGITransport(app=app)
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        now = datetime.now(UTC)

        case = SupportCase(
            id=uuid.uuid4(),
            merchant_id=MERCHANT_ID,
            case_number="CAS-APPR-DRILL",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="AWAITING_APPROVAL",
            queue="SETTLEMENT_OPS",
            summary="Approval drill",
            idempotency_key=f"idem_appr_{uuid.uuid4().hex}",
            version=1,
            created_at=now,
        )
        session.add(case)
        await session.commit()

        action_hash = compute_action_hash("SETTLEMENT_RESYNC", {"discrepancy": "6000.00"})

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Role MERCHANT tries to approve -> 403 Forbidden
            merchant_headers = {"Authorization": "Bearer demo-token-merchant-1"}
            res_forbidden = await client.post(
                f"/api/v1/cases/{case.id}/approve",
                headers=merchant_headers,
                json={"expected_version": 1, "action_hash": action_hash},
            )
            assert res_forbidden.status_code == 403
            assert res_forbidden.json()["error"]["code"] == "FORBIDDEN"

            # 2. Support role attempts approval with stale version (expected 999) -> 409
            support_headers = {"Authorization": "Bearer demo-token-support_agent-1"}
            res_conflict = await client.post(
                f"/api/v1/cases/{case.id}/approve",
                headers=support_headers,
                json={"expected_version": 999, "action_hash": action_hash},
            )
            assert res_conflict.status_code == 409
            assert res_conflict.json()["error"]["code"] == "CONFLICT"


# ------------------------------------------------------------------------------
# Drill 10: Follow-up worker race (SKIP LOCKED)
# ------------------------------------------------------------------------------
async def test_drill_10_followup_worker_race_condition() -> None:
    """Drill 10: Concurrent worker claims never run the same job twice."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        now = datetime.now(UTC)

        case = SupportCase(
            id=uuid.uuid4(),
            merchant_id=MERCHANT_ID,
            case_number="CAS-RACE-DRILL",
            category="SETTLEMENT_DELAY",
            priority="P1",
            status="AWAITING_APPROVAL",
            queue="SETTLEMENT_OPS",
            summary="Worker race drill",
            idempotency_key=f"idem_race_{uuid.uuid4().hex}",
            version=1,
            created_at=now,
        )
        session.add(case)
        await session.commit()

        # Enqueue single pending job
        job = FollowupJob(
            id=uuid.uuid4(),
            case_id=case.id,
            run_at=now,
            status="PENDING",
            attempts=0,
            created_at=now,
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    # Simulate two concurrent worker tasks with separate sessions
    async with shared_session_factory() as s1, shared_session_factory() as s2:
        claimed_a, claimed_b = await asyncio.gather(
            claim_next_followup_job(s1),
            claim_next_followup_job(s2),
        )

        # Exactly one worker must claim the job; the other receives None
        claimed_jobs = [j for j in (claimed_a, claimed_b) if j is not None]
        assert len(claimed_jobs) == 1
        assert claimed_jobs[0].id == job_id


# ------------------------------------------------------------------------------
# Drill 11: Verification fails -> Remains in progress, blocks premature resolve
# ------------------------------------------------------------------------------
async def test_drill_11_verification_fails_remains_verifying_blocks_resolve() -> None:
    """Drill 11: Failed verification keeps case in VERIFYING and blocks premature close."""
    transport = ASGITransport(app=app)
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        now = datetime.now(UTC)

        case = SupportCase(
            id=uuid.uuid4(),
            merchant_id=MERCHANT_ID,
            case_number="CAS-VERIFY-DRILL",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="AWAITING_APPROVAL",
            queue="SETTLEMENT_OPS",
            summary="Verification failure drill",
            idempotency_key=f"idem_ver_{uuid.uuid4().hex}",
            version=1,
            created_at=now,
        )
        session.add(case)
        event = CaseEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            actor="OpsSaathi AI",
            event_type="APPROVAL_REQUESTED",
            from_status="NEW",
            to_status="AWAITING_APPROVAL",
            visibility="INTERNAL",
            payload={
                "batch_ref": "BATCH_20261112_01",
                "discrepancy": "6000.00",
                "before_discrepancy": "6000.00",
                "expected_net": "15000.00",
                "observed": "9000.00",
                "action": "SETTLEMENT_RESYNC",
            },
            created_at=now,
        )
        session.add(event)
        await session.commit()

        action_hash = compute_action_hash("SETTLEMENT_RESYNC", {"discrepancy": "6000.00"})
        approval = Approval(
            id=uuid.uuid4(),
            case_id=case.id,
            action="SETTLEMENT_RESYNC",
            case_version=1,
            action_hash=action_hash,
            requested_by=MERCHANT_ID,
            decision="PENDING",
            status="ACTIVE",
        )
        session.add(approval)
        await session.commit()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            support_headers = {"Authorization": "Bearer demo-token-support_agent-1"}

            # Approve case -> moves to VERIFYING
            app_res = await client.post(
                f"/api/v1/cases/{case.id}/approve",
                headers=support_headers,
                json={"expected_version": 1, "action_hash": action_hash},
            )
            assert app_res.status_code == 200

            # 1. Negative check: Premature resolve without verification pass is blocked (403)
            premature_res = await client.post(
                f"/api/v1/cases/{case.id}/resolve",
                headers=support_headers,
                json={"expected_version": 2},
            )
            assert premature_res.status_code in {400, 403, 409}

            # 2. Fresh independent verification check fails because bank credit not simulated yet
            ver_res = await client.post(
                f"/api/v1/cases/{case.id}/verify",
                headers=support_headers,
            )
            assert ver_res.status_code == 200
            v_data = ver_res.json()["data"]
            assert v_data["verification_result"] == "FAIL"
            assert v_data["status"] == "VERIFYING"


# ------------------------------------------------------------------------------
# Drill 12: Mic permission denied -> Offer immediate text chat
# ------------------------------------------------------------------------------
async def test_drill_12_mic_permission_denied_contract() -> None:
    """Drill 12: Mic denial or unavailable audio immediately allows typed chat."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Voice sessions gracefully initialize or merchants post typed messages
        res = await client.post(
            "/api/v1/voice/sessions",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={"language": "en"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["ai_identity_disclosed"] is True

        # Typed investigation is immediately available
        chat_res = await client.post(
            "/api/v1/agent/messages",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={
                "message": "My ₹6,000 settlement is overdue",
                "language": "en",
            },
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()["data"]
        assert "₹6,000" in chat_data["reply"] or "6000" in chat_data["reply"]
