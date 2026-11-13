"""test_p5_a2_api_resilience.py: Comprehensive API Error and Resilience Tests (P5-A2).

Verifies PRD §9, §13, §14 and BUILD_PLAN P5-A2 requirements:
- HTTP 400 Bad Request / Validation errors (missing fields, bad parameters).
- HTTP 401 Unauthorized (missing/malformed tokens).
- HTTP 403 Forbidden (cross-merchant IDOR, role permission boundaries).
- HTTP 404 Not Found (nonexistent cases, merchants, runs).
- HTTP 409 Conflict (optimistic concurrency version conflicts).
- HTTP 429 Too Many Requests (in-memory sliding window rate limiting).
- HTTP 503 Service Unavailable (database or provider downtime).
- Idempotent retries without duplicate writes (case creation and settlement re-sync).
- Webhook deduplication (second delivery ignored safely).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.rate_limit import rate_limiter
from app.db.models import ResyncRequest, SupportCase
from app.db.seed import MERCHANT_ID
from app.db.session import get_db_session
from app.main import app
from app.tests.conftest import shared_session_factory
from app.tools.registry import ToolContext, run_request_settlement_resync
from app.tools.schemas import RequestSettlementResyncInput

pytestmark = pytest.mark.asyncio


# ------------------------------------------------------------------------------
# 1. HTTP 400 Validation Errors
# ------------------------------------------------------------------------------
async def test_400_validation_error_missing_body_fields() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Empty body on case creation
        res = await ac.post(
            "/api/v1/cases",
            headers={
                "Authorization": "Bearer demo-token-merchant-1",
                "Idempotency-Key": f"IDEMP-{uuid.uuid4()}",
            },
            json={},
        )
        assert res.status_code == 400
        payload = res.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "VALIDATION_ERROR"

        # 2. Missing Idempotency-Key header on case creation
        res_no_key = await ac.post(
            "/api/v1/cases",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={
                "category": "SETTLEMENT_MISMATCH",
                "priority": "P1",
                "summary": "Missing ₹6,000 settlement",
            },
        )
        assert res_no_key.status_code == 400
        assert res_no_key.json()["error"]["code"] == "VALIDATION_ERROR"

        # 3. Invalid queue name on case assign
        res_bad_queue = await ac.post(
            f"/api/v1/cases/{uuid.uuid4()}/assign",
            headers={"Authorization": "Bearer demo-token-supervisor-1"},
            json={"queue": "NON_EXISTENT_QUEUE", "expected_version": 1},
        )
        assert res_bad_queue.status_code == 400
        assert res_bad_queue.json()["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------------------------
# 2. HTTP 401 Unauthorized
# ------------------------------------------------------------------------------
async def test_401_unauthorized_missing_and_invalid_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Malformed token structure (no bearer prefix)
        res_no_bearer = await ac.get(
            "/api/v1/cases",
            headers={"Authorization": "demo-token-merchant-1"},
        )
        assert res_no_bearer.status_code == 401
        payload = res_no_bearer.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "UNAUTHORIZED"

        # 2. Invalid demo token format
        res_bad_token = await ac.get(
            "/api/v1/cases",
            headers={"Authorization": "Bearer not-a-valid-token-format"},
        )
        assert res_bad_token.status_code == 401
        assert res_bad_token.json()["error"]["code"] == "UNAUTHORIZED"

        # 3. Basic auth scheme instead of Bearer
        res_basic = await ac.get(
            "/api/v1/transactions",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert res_basic.status_code == 401
        assert res_basic.json()["error"]["code"] == "UNAUTHORIZED"

        # 4. Empty bearer token
        res_empty = await ac.get(
            "/api/v1/transactions",
            headers={"Authorization": "Bearer "},
        )
        assert res_empty.status_code == 401
        assert res_empty.json()["error"]["code"] == "UNAUTHORIZED"


# ------------------------------------------------------------------------------
# 3. HTTP 403 Forbidden
# ------------------------------------------------------------------------------
async def test_403_forbidden_cross_merchant_and_role_boundaries() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Merchant-1 attempting to access Merchant-2's profile (Cross-merchant IDOR)
        foreign_merchant_id = uuid.uuid4()
        res_idor = await ac.get(
            f"/api/v1/merchants/{foreign_merchant_id}",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
        )
        assert res_idor.status_code == 403
        payload = res_idor.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "FORBIDDEN"

        # 2. Merchant role attempting to approve action (Role escalation block)
        res_approve = await ac.post(
            f"/api/v1/cases/{uuid.uuid4()}/approve",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={
                "expected_version": 1,
                "action_hash": "a" * 64,
            },
        )
        assert res_approve.status_code == 403
        assert res_approve.json()["error"]["code"] == "FORBIDDEN"

        # 3. Merchant role attempting to assign case queue
        res_assign = await ac.post(
            f"/api/v1/cases/{uuid.uuid4()}/assign",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
            json={"queue": "SETTLEMENT_OPS", "expected_version": 1},
        )
        assert res_assign.status_code == 403
        assert res_assign.json()["error"]["code"] == "FORBIDDEN"


# ------------------------------------------------------------------------------
# 4. HTTP 404 Not Found
# ------------------------------------------------------------------------------
async def test_404_not_found_nonexistent_resources() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Nonexistent case ID requested by supervisor
        non_existent_case_id = uuid.uuid4()
        res_case = await ac.get(
            f"/api/v1/cases/{non_existent_case_id}",
            headers={"Authorization": "Bearer demo-token-supervisor-1"},
        )
        assert res_case.status_code == 404
        payload = res_case.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "NOT_FOUND"

        # 2. Nonexistent merchant requested by supervisor
        non_existent_merchant_id = uuid.uuid4()
        res_merchant = await ac.get(
            f"/api/v1/merchants/{non_existent_merchant_id}",
            headers={"Authorization": "Bearer demo-token-supervisor-1"},
        )
        assert res_merchant.status_code == 404
        assert res_merchant.json()["error"]["code"] == "NOT_FOUND"

        # 3. Nonexistent agent run SSE events
        res_run = await ac.get(
            f"/api/v1/agent/runs/{uuid.uuid4()}/events",
            headers={"Authorization": "Bearer demo-token-merchant-1"},
        )
        assert res_run.status_code == 404
        assert res_run.json()["error"]["code"] == "NOT_FOUND"


# ------------------------------------------------------------------------------
# 5. HTTP 409 Conflict (Optimistic Concurrency & Version Conflicts)
# ------------------------------------------------------------------------------
async def test_409_conflict_optimistic_concurrency() -> None:
    # Seed a case with version 2
    case_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with shared_session_factory() as session:
        case = SupportCase(
            id=case_id,
            merchant_id=MERCHANT_ID,
            case_number=f"CAS-{now.strftime('%Y%m%d')}-C409",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="AWAITING_APPROVAL",
            queue="SETTLEMENT_OPS",
            summary="Testing concurrency version conflict",
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            version=2,
            created_at=now,
        )
        session.add(case)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Stale version on approve (client sends expected_version=1, but DB has 2)
        res_approve = await ac.post(
            f"/api/v1/cases/{case_id}/approve",
            headers={"Authorization": "Bearer demo-token-supervisor-1"},
            json={
                "expected_version": 1,
                "action_hash": "b" * 64,
            },
        )
        assert res_approve.status_code == 409
        payload = res_approve.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "CONFLICT"

        # 2. Stale version on assign
        res_assign = await ac.post(
            f"/api/v1/cases/{case_id}/assign",
            headers={"Authorization": "Bearer demo-token-supervisor-1"},
            json={
                "expected_version": 1,
                "queue": "SETTLEMENT_OPS",
            },
        )
        assert res_assign.status_code == 409
        assert res_assign.json()["error"]["code"] == "CONFLICT"

        # 3. Stale version on reject
        res_reject = await ac.post(
            f"/api/v1/cases/{case_id}/reject",
            headers={"Authorization": "Bearer demo-token-supervisor-1"},
            json={
                "expected_version": 1,
                "action_hash": "b" * 64,
                "reason": "Test rejection",
            },
        )
        assert res_reject.status_code == 409
        assert res_reject.json()["error"]["code"] == "CONFLICT"


# ------------------------------------------------------------------------------
# 6. HTTP 429 Too Many Requests (Rate Limiting)
# ------------------------------------------------------------------------------
async def test_429_rate_limiting_sliding_window() -> None:
    rate_limiter.reset()
    test_ip = f"198.51.100.{uuid.uuid4().hex[:2]}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Fill the bucket up to max limit (120 requests)
        rate_limiter.requests[test_ip] = [1e10] * 120

        # Next request must be rate limited with 429
        res = await ac.post(
            "/api/v1/auth/demo-login",
            headers={"X-Forwarded-For": test_ip},
            json={"role": "MERCHANT"},
        )
        assert res.status_code == 429
        payload = res.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "RATE_LIMITED"
        assert "Rate limit exceeded" in payload["error"]["message"]

    rate_limiter.reset()


# ------------------------------------------------------------------------------
# 7. HTTP 503 Service Unavailable (Database Failure Resilience)
# ------------------------------------------------------------------------------
async def test_503_service_unavailable_database_failure() -> None:
    transport = ASGITransport(app=app)

    async def mock_failing_session() -> None:
        raise OperationalError("SELECT 1", {}, Exception("Connection refused"))

    app.dependency_overrides[get_db_session] = mock_failing_session
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get(
                "/api/v1/cases",
                headers={"Authorization": "Bearer demo-token-supervisor-1"},
            )
            assert res.status_code == 503
            payload = res.json()
            assert payload["ok"] is False
            assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"
            assert payload["error"]["details"] == {"service": "database"}
    finally:
        from app.tests.conftest import override_get_db

        app.dependency_overrides[get_db_session] = override_get_db


# ------------------------------------------------------------------------------
# 8. Retry Without Duplicate Write (Idempotency)
# ------------------------------------------------------------------------------
async def test_retry_without_duplicate_write_case_creation() -> None:
    idempotency_key = f"IDEMP-TEST-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "category": "SETTLEMENT_MISMATCH",
            "priority": "P1",
            "summary": "Missing ₹6,000 from settlement batch",
        }

        # 1. Initial creation
        res1 = await ac.post(
            "/api/v1/cases",
            headers={
                "Authorization": "Bearer demo-token-merchant-1",
                "Idempotency-Key": idempotency_key,
            },
            json=req_body,
        )
        assert res1.status_code == 200
        data1 = res1.json()["data"]
        case_id_1 = data1["id"]

        # 2. Retry with same Idempotency-Key
        res2 = await ac.post(
            "/api/v1/cases",
            headers={
                "Authorization": "Bearer demo-token-merchant-1",
                "Idempotency-Key": idempotency_key,
            },
            json=req_body,
        )
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        case_id_2 = data2["id"]

        # Both must return the same case ID
        assert case_id_1 == case_id_2

    # 3. Verify exactly one row in the database
    async with shared_session_factory() as session:
        stmt = select(SupportCase).where(SupportCase.idempotency_key == idempotency_key)
        rows = list((await session.execute(stmt)).scalars().all())
        assert len(rows) == 1
        assert str(rows[0].id) == case_id_1


async def test_resync_request_idempotency_prevents_duplicate_send() -> None:
    idempotency_key = f"RESYNC-KEY-{uuid.uuid4()}"
    now = datetime.now(UTC)

    async with shared_session_factory() as session:
        # Pre-seed a support case to satisfy FK constraint
        case_id = uuid.uuid4()
        case = SupportCase(
            id=case_id,
            merchant_id=MERCHANT_ID,
            case_number=f"CAS-{now.strftime('%Y%m%d')}-RSYNC",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="IN_PROGRESS",
            queue="SETTLEMENT_OPS",
            summary="Pre-seeded case for resync idempotency",
            idempotency_key=f"IDEMP-RSYNC-{uuid.uuid4()}",
            version=1,
            created_at=now,
        )
        session.add(case)
        await session.commit()

        # Pre-seed existing re-sync request
        existing = ResyncRequest(
            id=uuid.uuid4(),
            case_id=case_id,
            batch_ref="BATCH_20261112_01",
            status="ACKNOWLEDGED",
            idempotency_key=idempotency_key,
            adapter_ref="MOCK_SETTLEMENT_OPS",
            created_at=now,
        )
        session.add(existing)
        await session.commit()

        ctx = ToolContext(merchant_id=MERCHANT_ID, session=session)
        tool_input = RequestSettlementResyncInput(
            case_id=str(case_id),
            batch_ref="BATCH_20261112_01",
            amount=Decimal("6000.00"),
            idempotency_key=idempotency_key,
        )

        # Execute tool with duplicate idempotency key
        output = await run_request_settlement_resync(tool_input, ctx)
        assert output.status == "ACKNOWLEDGED"

        # Verify only one record exists in DB
        stmt = select(ResyncRequest).where(ResyncRequest.idempotency_key == idempotency_key)
        records = list((await session.execute(stmt)).scalars().all())
        assert len(records) == 1


# ------------------------------------------------------------------------------
# 9. Duplicate Webhook Deduplication
# ------------------------------------------------------------------------------
async def test_duplicate_webhook_deduplication() -> None:
    from app.tests.conftest import generate_test_paytm_checksum

    event_id = f"ORDER_DUP_{uuid.uuid4().hex[:8]}"
    params = {
        "event_id": event_id,
        "ORDERID": event_id,
        "TXNAMOUNT": "6000.00",
        "STATUS": "TXN_SUCCESS",
    }
    checksum = generate_test_paytm_checksum(params)
    payload = {
        **params,
        "CHECKSUMHASH": checksum,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. First webhook delivery
        res1 = await ac.post(
            "/api/v1/webhooks/paytm",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        assert res1.status_code == 200
        data1 = res1.json()["data"]
        assert data1["received"] is True
        assert data1["event_id"] == event_id
        assert data1["status"] == "PROCESSED"
        assert data1["deduplicated"] is True

        # 2. Redelivery of identical webhook
        res2 = await ac.post(
            "/api/v1/webhooks/paytm",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        assert data2["received"] is True
        assert data2["event_id"] == event_id
        assert data2["status"] == "DUPLICATE_IGNORED"
        assert data2["deduplicated"] is False
