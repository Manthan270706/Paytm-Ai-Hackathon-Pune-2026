import uuid

from fastapi.testclient import TestClient

from app.db.seed import MERCHANT_ID
from app.main import app

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
    # Accessing own merchant profile returns 200
    res = client.get(
        f"/api/v1/merchants/{MERCHANT_ID}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["data"]["id"] == str(MERCHANT_ID)
    assert data["data"]["display_name"] == "Two Bits Chai & Snacks"


def test_transaction_routes() -> None:
    # List transactions
    list_res = client.get(
        "/api/v1/transactions",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["ok"] is True
    assert len(data["data"]["items"]) >= 1

    # Get transaction detail
    txn_id = data["data"]["items"][0]["id"]
    detail_res = client.get(
        f"/api/v1/transactions/{txn_id}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["ok"] is True

    # Unknown transaction ID returns 404
    unknown_res = client.get(
        f"/api/v1/transactions/{uuid.uuid4()}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert unknown_res.status_code == 404


def test_settlements_route() -> None:
    res = client.get(
        "/api/v1/settlements",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "batches" in data["data"]
    assert "discrepancy_amount" in data["data"]


def test_agent_message_route() -> None:
    res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"message": "My ₹6,000 payment is missing from settlement", "language": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["data"]["intent"] == "SETTLEMENT_MISMATCH"
    assert "evidence_summary" in data["data"]


def test_voice_routes() -> None:
    # Create voice session
    session_res = client.post(
        "/api/v1/voice/sessions",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"language": "en"},
    )
    assert session_res.status_code == 200
    s_data = session_res.json()
    assert s_data["ok"] is True
    assert s_data["data"]["ai_identity_disclosed"] is True

    # Voice transcription
    conv_id = uuid.uuid4()
    trans_res = client.post(
        "/api/v1/voice/transcriptions",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
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
    bad_create = client.post(
        "/api/v1/cases",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"summary": "Missing settlement"},
    )
    assert bad_create.status_code == 400

    # Case creation with Idempotency-Key succeeds
    idemp_key = f"IDEMP-{uuid.uuid4()}"
    create_res = client.post(
        "/api/v1/cases",
        headers={
            "Idempotency-Key": idemp_key,
            "Authorization": "Bearer demo-token-merchant-1",
        },
        json={
            "category": "SETTLEMENT_MISMATCH",
            "summary": "Missing ₹6,000 from settlement batch BATCH_01",
        },
    )
    assert create_res.status_code == 200
    case_data = create_res.json()
    assert case_data["ok"] is True
    case_id = case_data["data"]["id"]
    version = case_data["data"]["version"]

    # Get case detail with timeline
    detail_res = client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert detail_res.status_code == 200
    assert len(detail_res.json()["data"]["timeline"]) >= 1

    # Merchant cannot approve (403)
    merchant_app_res = client.post(
        f"/api/v1/cases/{case_id}/approve",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"expected_version": version, "action_hash": "hash123"},
    )
    assert merchant_app_res.status_code == 403

    # Merchant cannot reject (403)
    merchant_rej_res = client.post(
        f"/api/v1/cases/{case_id}/reject",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"expected_version": version, "action_hash": "hash123", "reason": "unauthorized"},
    )
    assert merchant_rej_res.status_code == 403

    # Merchant cannot assign (403)
    merchant_assign_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"expected_version": version, "queue": "SETTLEMENT_OPS"},
    )
    assert merchant_assign_res.status_code == 403

    # Invalid queue validation (400)
    bad_queue_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={"expected_version": version, "queue": "INVALID_QUEUE"},
    )
    assert bad_queue_res.status_code == 400

    # Assign queue as support role succeeds
    assign_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={"expected_version": version, "queue": "ESCALATIONS"},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["data"]["queue"] == "ESCALATIONS"
    version = assign_res.json()["data"]["new_version"]

    # Approve case action as support role
    app_res = client.post(
        f"/api/v1/cases/{case_id}/approve",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={"expected_version": version, "action_hash": "hash123"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["data"]["status"] == "APPROVED"
    version = app_res.json()["data"]["new_version"]

    # Reject case action as support role
    rej_res = client.post(
        f"/api/v1/cases/{case_id}/reject",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={
            "expected_version": version,
            "action_hash": "hash123",
            "reason": "Requires bank UTR",
        },
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["data"]["status"] == "REJECTED"

    # Verify case rejects with 409 CONFLICT because status is REJECTED (not VERIFYING)
    ver_res = client.post(
        f"/api/v1/cases/{case_id}/verify",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    )
    assert ver_res.status_code == 409
    assert ver_res.json()["error"]["code"] == "CONFLICT"

    # Premature resolution attempt without verification PASS is blocked (403)
    premature_res = client.post(
        f"/api/v1/cases/{case_id}/resolve",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    )
    assert premature_res.status_code == 403

    # Merchant cannot resolve (403)
    merchant_resolve_res = client.post(
        f"/api/v1/cases/{case_id}/resolve",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert merchant_resolve_res.status_code == 403


def test_demo_and_metrics_routes() -> None:
    # Reset demo
    reset_res = client.post(
        "/api/v1/demo/reset",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["data"]["discrepancy"] == "6000.00"

    # Simulate settlement
    sim_res = client.post(
        "/api/v1/demo/simulate-settlement",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={"amount": "6000.00", "batch_ref": "BATCH_01"},
    )
    assert sim_res.status_code == 200
    assert sim_res.json()["ok"] is True

    # Metrics
    metrics_res = client.get(
        "/api/v1/metrics",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
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
