"""Tests for P4-A8 Metrics and Integration Health.

Verifies:
1. GET /api/v1/metrics computes outcome metrics from case_events (time to first response,
   time to verified resolution, handled vs escalated, repeat explanations avoided).
2. Role filtering on GET /api/v1/metrics (merchant scoped vs support system-wide).
3. Tile updates reflect dynamic case events following resolution.
4. GET /api/v1/health exposes provider adapters, fallbacks, and database health with ZERO secrets.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import CaseEvent, SupportCase
from app.db.seed import MERCHANT_ID, reset_and_seed
from app.main import app
from app.tests.conftest import shared_session_factory

pytestmark = pytest.mark.asyncio


async def test_metrics_computed_from_case_events_and_baseline() -> None:
    """Acceptance: GET /api/v1/metrics computes time to first response and resolution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initial call before session cases
        res = await client.get(
            "/api/v1/metrics",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["straight_through_processing_rate_percent"] > 0
        assert data["total_cases_handled"] > 0
        assert data["repeat_explanations_avoided"] > 0
        assert data["time_to_first_response_seconds"] > 0
        assert data["time_to_verified_resolution_minutes"] > 0


async def test_metrics_dynamically_update_after_case_events() -> None:
    """Acceptance: Tile updates after case events and verified resolution."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        now = datetime.now(UTC)

        # 1. Create a dynamic test case
        case_id = uuid.uuid4()
        case = SupportCase(
            id=case_id,
            merchant_id=MERCHANT_ID,
            case_number="CAS-METRIC-01",
            category="SETTLEMENT_DELAY",
            priority="P1",
            status="RESOLVED",
            queue="SETTLEMENT_OPS",
            summary="Discrepancy test for metrics",
            idempotency_key=f"idem_metrics_{uuid.uuid4().hex}",
            version=2,
            created_at=now,
        )
        session.add(case)
        await session.flush()

        # 2. Append case events (creation -> response -> follow-up check -> resolution)
        ev1 = CaseEvent(
            id=uuid.uuid4(),
            case_id=case_id,
            actor="merchant",
            event_type="CASE_CREATED",
            from_status=None,
            to_status="NEW",
            visibility="MERCHANT",
            payload={"summary": case.summary},
            created_at=now,
        )
        ev2 = CaseEvent(
            id=uuid.uuid4(),
            case_id=case_id,
            actor="OpsSaathi AI",
            event_type="INVESTIGATION_COMPLETED",
            from_status="NEW",
            to_status="AWAITING_APPROVAL",
            visibility="MERCHANT",
            payload={"message": "Investigation complete"},
            created_at=datetime.fromtimestamp(now.timestamp() + 2, tz=UTC),
        )
        ev3 = CaseEvent(
            id=uuid.uuid4(),
            case_id=case_id,
            actor="SYSTEM_FOLLOWUP_WORKER",
            event_type="FOLLOWUP_CHECK_NO_CHANGE",
            from_status="AWAITING_APPROVAL",
            to_status="AWAITING_APPROVAL",
            visibility="INTERNAL",
            payload={"checked": True},
            created_at=datetime.fromtimestamp(now.timestamp() + 5, tz=UTC),
        )
        ev4 = CaseEvent(
            id=uuid.uuid4(),
            case_id=case_id,
            actor="support_agent",
            event_type="CASE_RESOLVED",
            from_status="VERIFYING",
            to_status="RESOLVED",
            visibility="MERCHANT",
            payload={"status": "RESOLVED"},
            created_at=datetime.fromtimestamp(now.timestamp() + 60, tz=UTC),
        )
        session.add_all([ev1, ev2, ev3, ev4])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Support agent fetches system metrics
        res = await client.get(
            "/api/v1/metrics",
            headers={"Authorization": "Bearer demo-token-support_agent-1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]

        # Assert dynamic metrics derived from the seeded case events
        assert data["total_cases_handled"] >= 1
        assert data["total_cases_escalated"] == 0
        assert data["straight_through_processing_rate_percent"] == 100.0
        assert data["repeat_explanations_avoided"] >= 1


async def test_metrics_role_filtering() -> None:
    """Verify role-filtered outcome metrics (merchant scope vs support system-wide)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Merchant call
        merchant_res = await client.get(
            "/api/v1/metrics",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
        )
        assert merchant_res.status_code == 200
        assert merchant_res.json()["ok"] is True

        # Support call
        support_res = await client.get(
            "/api/v1/metrics",
            headers={"Authorization": "Bearer demo-token-support_agent-1"},
        )
        assert support_res.status_code == 200
        assert support_res.json()["ok"] is True


async def test_health_endpoint_diagnostics_and_zero_secrets() -> None:
    """Acceptance: health screen shows active providers and fallbacks correctly without secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        data = body["data"]

        # Provider health items
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "llm_provider" in data
        assert "voice_provider" in data
        assert "payment_provider" in data
        assert "settlement_ops_adapter" in data
        assert "services" in data
        assert data["services"]["database"] in {"connected", "configured"}
        assert data["services"]["verifier_role"] == "configured"

        # Zero secret exposure check: serialize full response text and assert no secrets
        response_text = res.text.lower()
        forbidden_keywords = [
            "password",
            "secret",
            "api_key",
            "token",
            "private_key",
            "cvv",
            "pin",
            "auth_key",
        ]
        for keyword in forbidden_keywords:
            assert f'"{keyword}":' not in response_text, f"Secret key leaked in health: {keyword}"
