from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_golden_path_end_to_end() -> None:
    # 1. Reset demo environment to frozen baseline
    reset_res = client.post("/api/v1/demo/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["ok"] is True
    assert reset_res.json()["data"]["discrepancy"] == "6000.00"

    # 2. Merchant lodges complaint
    msg_res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={
            "message": "My ₹6,000 payment from yesterday is missing from settlement",
            "language": "en",
        },
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["ok"] is True
    case_id = msg_data["data"]["active_case_id"]
    assert case_id is not None

    # 3. Fetch case detail as support agent
    detail_res = client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    )
    assert detail_res.status_code == 200
    c_detail = detail_res.json()["data"]
    assert c_detail["status"] == "AWAITING_APPROVAL"
    version = c_detail["version"]
    assert c_detail["pending_approval"] is not None
    action_hash = c_detail["pending_approval"]["action_hash"]

    # Support sees all events (including INTERNAL)
    support_timeline = c_detail["timeline"]
    assert any(e["visibility"] == "INTERNAL" for e in support_timeline)

    # 4. Merchant view hides internal notes/events
    merchant_detail_res = client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert merchant_detail_res.status_code == 200
    merchant_timeline = merchant_detail_res.json()["data"]["timeline"]
    assert all(e["visibility"] != "INTERNAL" for e in merchant_timeline)

    # 5. Premature resolution attempt before approval is blocked (403)
    early_resolve_res = client.post(
        f"/api/v1/cases/{case_id}/resolve",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    )
    assert early_resolve_res.status_code == 403

    # 6. Support agent approves settlement re-sync
    app_res = client.post(
        f"/api/v1/cases/{case_id}/approve",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
        json={
            "expected_version": version,
            "action_hash": action_hash,
        },
    )
    assert app_res.status_code == 200
    assert app_res.json()["data"]["status"] == "APPROVED"
    assert app_res.json()["data"]["resync_status"] == "ACKNOWLEDGED"

    # Case transitions to VERIFYING
    post_app_detail = client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    ).json()["data"]
    assert post_app_detail["status"] == "VERIFYING"
    version = post_app_detail["version"]

    # 7. Negative Test: Resolution before bank settlement credit is blocked (403)
    premature_close_res = client.post(
        f"/api/v1/cases/{case_id}/resolve",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    )
    assert premature_close_res.status_code == 403
    assert "verification PASS" in premature_close_res.json()["error"]["message"]

    # 8. Early verification check fails while ledger is unchanged
    early_verify_res = client.post(f"/api/v1/cases/{case_id}/verify")
    assert early_verify_res.status_code == 200
    assert early_verify_res.json()["data"]["verification_result"] == "FAIL"
    assert early_verify_res.json()["data"]["status"] == "VERIFYING"

    # 9. Simulate bank settlement credit (inserts ₹6,000 SYNTHETIC_DEMO entry)
    sim_res = client.post(
        "/api/v1/demo/simulate-settlement",
        json={"amount": "6000.00", "batch_ref": "BATCH_20261112_01"},
    )
    assert sim_res.status_code == 200
    assert sim_res.json()["data"]["source_type"] == "SYNTHETIC_DEMO"

    # 10. Fresh independent verification succeeds through read-only verifier session
    verify_res = client.post(f"/api/v1/cases/{case_id}/verify")
    assert verify_res.status_code == 200
    v_data = verify_res.json()["data"]
    assert v_data["verification_result"] == "PASS"
    assert v_data["status"] == "RESOLVED"
    assert v_data["before_observed"] == "9000.00"
    assert v_data["after_observed"] == "15000.00"
    assert v_data["verifier_role"] == "opssaathi_verifier"

    # 11. Final case detail is RESOLVED with complete audit trail
    final_detail = client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": "Bearer demo-token-support_agent-1"},
    ).json()["data"]
    assert final_detail["status"] == "RESOLVED"
    event_types = [e["event_type"] for e in final_detail["timeline"]]
    assert "APPROVAL_GRANTED" in event_types
    assert "RESYNC_REQUESTED" in event_types
    assert "VERIFICATION_COMPLETED" in event_types
