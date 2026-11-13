import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import AsyncSession, _create_engine, async_sessionmaker, get_db_session
from app.main import app

TEST_ROUTES_DB = "sqlite+aiosqlite:///./test_routes.db"
test_engine = _create_engine(TEST_ROUTES_DB, is_verifier=False)
route_session_factory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with route_session_factory() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(autouse=True, scope="module")
async def setup_route_test_db() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists("./test_routes.db"):
        os.remove("./test_routes.db")


client = TestClient(app)


def test_auth_routes() -> None:
    # Demo login
    login_res = client.post("/api/v1/auth/demo-login", json={"role": "MERCHANT"})
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["ok"] is True
    assert login_data["data"]["role"] == "MERCHANT"
    assert "access_token" in login_data["data"]

    # Current user /me
    me_res = client.get("/api/v1/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["ok"] is True
    assert me_data["data"]["role"] == "MERCHANT"


def test_merchant_route() -> None:
    merchant_id = uuid.uuid4()
    res = client.get(f"/api/v1/merchants/{merchant_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["data"]["id"] == str(merchant_id)
    assert data["data"]["display_name"] == "Ramesh Kirana Store"


def test_transaction_routes() -> None:
    # List transactions
    list_res = client.get("/api/v1/transactions")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["ok"] is True
    assert len(data["data"]["items"]) >= 1

    # Get transaction detail
    txn_id = uuid.uuid4()
    detail_res = client.get(f"/api/v1/transactions/{txn_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["ok"] is True
    assert detail_data["data"]["id"] == str(txn_id)


def test_settlements_route() -> None:
    res = client.get("/api/v1/settlements")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "batches" in data["data"]
    assert "discrepancy_amount" in data["data"]


def test_agent_message_route() -> None:
    res = client.post(
        "/api/v1/agent/messages",
        json={"message": "My ₹6,000 payment is missing from settlement", "language": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["data"]["intent"] == "SETTLEMENT_MISMATCH"
    assert "evidence_summary" in data["data"]


def test_voice_routes() -> None:
    # Create voice session
    session_res = client.post("/api/v1/voice/sessions", json={"language": "en"})
    assert session_res.status_code == 200
    s_data = session_res.json()
    assert s_data["ok"] is True
    assert s_data["data"]["ai_identity_disclosed"] is True

    # Voice transcription
    conv_id = uuid.uuid4()
    trans_res = client.post(
        "/api/v1/voice/transcriptions",
        json={
            "conversation_id": str(conv_id),
            "transcript": "Check my settlement",
            "language": "en",
        },
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["ok"] is True


def test_case_lifecycle_routes() -> None:
    # Case creation without Idempotency-Key fails with 400
    bad_create = client.post("/api/v1/cases", json={"summary": "Missing settlement"})
    assert bad_create.status_code == 400

    # Case creation with Idempotency-Key succeeds
    idemp_key = f"IDEMP-{uuid.uuid4()}"
    create_res = client.post(
        "/api/v1/cases",
        headers={"Idempotency-Key": idemp_key},
        json={"summary": "Missing ₹6,000 from settlement batch BATCH_01"},
    )
    assert create_res.status_code == 200
    case_data = create_res.json()
    assert case_data["ok"] is True
    case_id = case_data["data"]["id"]
    version = case_data["data"]["version"]

    # Get case detail with timeline
    detail_res = client.get(f"/api/v1/cases/{case_id}")
    assert detail_res.status_code == 200
    assert len(detail_res.json()["data"]["timeline"]) >= 1

    # Approve case action
    app_res = client.post(
        f"/api/v1/cases/{case_id}/approve",
        json={"expected_version": version, "action_hash": "hash123"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["data"]["status"] == "APPROVED"

    # Reject case action
    rej_res = client.post(
        f"/api/v1/cases/{case_id}/reject",
        json={
            "expected_version": version + 1,
            "action_hash": "hash123",
            "reason": "Requires bank UTR",
        },
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["data"]["status"] == "REJECTED"

    # Verify case
    ver_res = client.post(f"/api/v1/cases/{case_id}/verify")
    assert ver_res.status_code == 200
    assert ver_res.json()["data"]["verification_result"] == "PASS"
    assert ver_res.json()["data"]["verifier_role"] == "opssaathi_verifier"


def test_demo_and_metrics_routes() -> None:
    # Reset demo (seeds the DB)
    reset_res = client.post("/api/v1/demo/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["data"]["discrepancy"] == "6000.00"

    # Simulate settlement
    sim_res = client.post(
        "/api/v1/demo/simulate-settlement", json={"amount": "6000.00", "batch_ref": "BATCH_01"}
    )
    assert sim_res.status_code == 200
    assert sim_res.json()["ok"] is True

    # Metrics
    metrics_res = client.get("/api/v1/metrics")
    assert metrics_res.status_code == 200
    assert metrics_res.json()["data"]["straight_through_processing_rate_percent"] > 0


def test_paytm_webhook_route() -> None:
    webhook_res = client.post(
        "/api/v1/webhooks/paytm",
        json={
            "event_id": f"EVT-{uuid.uuid4()}",
            "provider_txn_id": "TXN_78456321",
            "order_id": "ORD_01",
            "amount": "6000.00",
            "status": "SUCCESS",
            "checksum": "mock_checksum_abc123",
        },
    )
    assert webhook_res.status_code == 200
    assert webhook_res.json()["data"]["received"] is True
