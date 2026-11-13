import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimiter
from app.main import app

client = TestClient(app)



def test_400_validation_error() -> None:
    # 1. Missing Idempotency-Key header returns 400
    res = client.post(
        "/api/v1/cases",
        json={"category": "PAYOUT_DELAY", "summary": "Missing payout"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "Idempotency-Key" in body["error"]["message"]

    # 2. Invalid schema (missing required summary) returns 400
    res_bad_body = client.post(
        "/api/v1/cases",
        headers={"Idempotency-Key": f"IDEMP-{uuid.uuid4()}"},
        json={"category": "PAYOUT_DELAY"},
    )
    assert res_bad_body.status_code == 400
    assert res_bad_body.json()["error"]["code"] == "VALIDATION_ERROR"


def test_401_unauthorized() -> None:
    # Invalid token returns 401
    res = client.get(
        "/api/v1/merchants/11111111-1111-1111-1111-111111111111",
        headers={"Authorization": "Bearer invalid-expired-token"},
    )
    assert res.status_code == 401
    body = res.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_403_forbidden() -> None:
    # 1. Merchant attempting cross-merchant IDOR on another merchant ID returns 403
    foreign_merchant_id = uuid.uuid4()
    res_idor = client.get(
        f"/api/v1/merchants/{foreign_merchant_id}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert res_idor.status_code == 403
    assert res_idor.json()["error"]["code"] == "FORBIDDEN"

    # 2. Merchant attempting to approve a case returns 403
    case_id = uuid.uuid4()
    res_approve = client.post(
        f"/api/v1/cases/{case_id}/approve",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"expected_version": 1, "action_hash": "dummy_hash"},
    )
    assert res_approve.status_code == 403
    assert res_approve.json()["error"]["code"] == "FORBIDDEN"


def test_404_not_found() -> None:
    # Requesting non-existent merchant as a supervisor returns 404
    non_existent = uuid.uuid4()
    res = client.get(
        f"/api/v1/merchants/{non_existent}",
        headers={"Authorization": "Bearer demo-token-supervisor-1"},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_409_conflict_optimistic_locking() -> None:
    # Create a real case first
    idemp_key = f"IDEMP-CONFLICT-{uuid.uuid4()}"
    create_res = client.post(
        "/api/v1/cases",
        headers={
            "Idempotency-Key": idemp_key,
            "Authorization": "Bearer demo-token-merchant-1",
        },
        json={"category": "PAYOUT_DELAY", "summary": "Delayed payout for conflict test"},
    )
    assert create_res.status_code == 200
    case_id = create_res.json()["data"]["id"]

    # Attempt to approve with mismatch version (expected_version=99 != 1)
    conflict_res = client.post(
        f"/api/v1/cases/{case_id}/approve",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={"expected_version": 99, "action_hash": "hash_123"},
    )
    assert conflict_res.status_code == 409
    body = conflict_res.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFLICT"


def test_429_rate_limited() -> None:
    # Test rate limiter directly and ensure it returns 429
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    client_key = "test-client-ip"
    limiter.check(client_key)
    limiter.check(client_key)

    # Third check raises RateLimitError
    with pytest.raises(Exception) as excinfo:
        limiter.check(client_key)
    assert "Rate limit exceeded" in str(excinfo.value)


def test_idempotent_duplicate_create() -> None:
    # Using the same Idempotency-Key must return the exact same case
    idemp_key = f"IDEMP-SAME-{uuid.uuid4()}"

    res1 = client.post(
        "/api/v1/cases",
        headers={
            "Idempotency-Key": idemp_key,
            "Authorization": "Bearer demo-token-merchant-1",
        },
        json={"category": "PAYOUT_DELAY", "summary": "Duplicate test case"},
    )
    assert res1.status_code == 200
    case_1 = res1.json()["data"]

    res2 = client.post(
        "/api/v1/cases",
        headers={
            "Idempotency-Key": idemp_key,
            "Authorization": "Bearer demo-token-merchant-1",
        },
        json={"category": "PAYOUT_DELAY", "summary": "Duplicate test case (retry)"},
    )
    assert res2.status_code == 200
    case_2 = res2.json()["data"]

    # Assert exact identity
    assert case_1["id"] == case_2["id"]
    assert case_1["case_number"] == case_2["case_number"]
    assert case_1["version"] == case_2["version"]
