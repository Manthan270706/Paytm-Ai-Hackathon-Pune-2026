import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Approval, ResyncRequest
from app.db.seed import MERCHANT_ID, reset_and_seed
from app.domain.approvals import compute_action_hash
from app.main import app
from app.tests.conftest import shared_session_factory
from app.tools.registry import (
    ApplyCaseUpdateInput,
    AssignCaseInput,
    CreateSupportCaseInput,
    RequestApprovalInput,
    RequestSettlementResyncInput,
    SendMerchantUpdateInput,
    ToolContext,
    run_apply_case_update,
    run_assign_case,
    run_create_support_case,
    run_request_approval,
    run_request_settlement_resync,
    run_send_merchant_update,
)

client = TestClient(app)


@pytest.mark.asyncio
async def test_p3_a3_tools_direct() -> None:
    """Test case creation, assignment, approval request, and settlement re-sync tools."""
    async with shared_session_factory() as session:
        await reset_and_seed(session)
        ctx = ToolContext(merchant_id=MERCHANT_ID, session=session)

        # 1. create_support_case with idempotency
        idemp = f"IDEMP-TEST-{uuid.uuid4().hex[:8]}"
        out_case1 = await run_create_support_case(
            CreateSupportCaseInput(
                category="SETTLEMENT_MISMATCH",
                summary="Missing ₹6,000 settlement batch BATCH_01",
                priority="P1",
                idempotency_key=idemp,
            ),
            ctx,
        )
        assert out_case1.status == "NEW"
        assert out_case1.queue == "SETTLEMENT_OPS"

        # Retry with same idempotency key must return exact same case
        out_case2 = await run_create_support_case(
            CreateSupportCaseInput(
                category="SETTLEMENT_MISMATCH",
                summary="Missing ₹6,000 settlement batch BATCH_01",
                priority="P1",
                idempotency_key=idemp,
            ),
            ctx,
        )
        assert out_case2.case_id == out_case1.case_id
        assert out_case2.case_number == out_case1.case_number

        # 2. assign_case to SETTLEMENT_OPS
        out_assign = await run_assign_case(
            AssignCaseInput(
                case_id=out_case1.case_id,
                queue="SETTLEMENT_OPS",
                reason="Routing to settlement ops team",
            ),
            ctx,
        )
        assert out_assign.queue == "SETTLEMENT_OPS"

        # 3. request_approval for ₹6,000 (above ₹5,000 threshold)
        expected_hash = compute_action_hash(
            "SETTLEMENT_RESYNC",
            {"discrepancy": "6000.00"},
        )
        out_appr = await run_request_approval(
            RequestApprovalInput(
                case_id=out_case1.case_id,
                action="SETTLEMENT_RESYNC",
                amount=Decimal("6000.00"),
                evidence={"expected_net": "15000.00", "observed_net": "9000.00"},
            ),
            ctx,
        )
        assert out_appr.status == "PENDING"
        assert out_appr.action_hash == expected_hash

        # Verify Approval record in database
        stmt_appr = select(Approval).where(Approval.id == uuid.UUID(out_appr.approval_id))
        appr_record = (await session.execute(stmt_appr)).scalar_one_or_none()
        assert appr_record is not None
        assert appr_record.action == "SETTLEMENT_RESYNC"
        assert appr_record.action_hash == expected_hash
        assert appr_record.status == "ACTIVE"

        # 4. request_settlement_resync creates ResyncRequest row with adapter reference
        resync_idemp = f"RESYNC-IDEMP-{uuid.uuid4().hex[:8]}"
        out_resync1 = await run_request_settlement_resync(
            RequestSettlementResyncInput(
                case_id=out_case1.case_id,
                batch_ref="BATCH_20261112_01",
                amount=Decimal("6000.00"),
                idempotency_key=resync_idemp,
            ),
            ctx,
        )
        assert out_resync1.status == "ACKNOWLEDGED"
        assert out_resync1.adapter_ref == "MOCK_SETTLEMENT_OPS_ACK_2026"

        # Idempotent re-sync with same key returns identical record
        out_resync2 = await run_request_settlement_resync(
            RequestSettlementResyncInput(
                case_id=out_case1.case_id,
                batch_ref="BATCH_20261112_01",
                amount=Decimal("6000.00"),
                idempotency_key=resync_idemp,
            ),
            ctx,
        )
        assert out_resync2.resync_id == out_resync1.resync_id

        # Verify row in resync_requests table
        stmt_resync = select(ResyncRequest).where(
            ResyncRequest.id == uuid.UUID(out_resync1.resync_id)
        )
        resync_row = (await session.execute(stmt_resync)).scalar_one_or_none()
        assert resync_row is not None
        assert resync_row.batch_ref == "BATCH_20261112_01"
        assert resync_row.status == "ACKNOWLEDGED"

        # 5. apply_case_update
        out_update = await run_apply_case_update(
            ApplyCaseUpdateInput(
                case_id=out_case1.case_id,
                to_status="IN_PROGRESS",
                expected_version=out_appr.case_version,
                note="Investigation completed, resync pending",
            ),
            ctx,
        )
        assert out_update.status == "IN_PROGRESS"

        # 6. send_merchant_update
        out_msg = await run_send_merchant_update(
            SendMerchantUpdateInput(
                case_id=out_case1.case_id,
                template="APPROVAL_SUBMITTED",
                language="en",
                parameters={"amount": "6000.00"},
            ),
            ctx,
        )
        assert out_msg.delivered is True
        assert out_msg.channel == "IN_APP"


def test_p3_a3_agent_flow_above_threshold() -> None:
    """End-to-end agent turn: ₹6,000 complaint triggers case creation and waits for approval."""
    res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={
            "message": "My ₹6,000 payment from yesterday is missing from settlement",
            "language": "en",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["active_case_id"] is not None

    evidence = data["evidence_summary"]
    assert evidence["expected_net"] == "15000.00"
    assert evidence["observed_net"] == "9000.00"
    assert evidence["discrepancy"] == "6000.00"
    assert evidence["reason_code"] == "OVERDUE"
    assert evidence["source_type"] == "SYNTHETIC_DEMO"

    # Case detail must exist and be awaiting approval
    case_res = client.get(
        f"/api/v1/cases/{data['active_case_id']}",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert case_res.status_code == 200
    case_data = case_res.json()["data"]
    assert case_data["queue"] == "SETTLEMENT_OPS"
    assert case_data["status"] == "AWAITING_APPROVAL"
    assert len(case_data["timeline"]) >= 2
