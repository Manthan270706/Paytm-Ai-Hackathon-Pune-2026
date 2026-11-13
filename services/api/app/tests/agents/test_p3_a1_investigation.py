from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db.seed import MERCHANT_ID, reset_and_seed
from app.main import app
from app.tests.conftest import shared_session_factory
from app.tools.registry import (
    CalculateDiscrepancyInput,
    FindTransactionsInput,
    GetMerchantContextInput,
    GetSettlementEntriesInput,
    ToolContext,
    run_calculate_discrepancy,
    run_find_transactions,
    run_get_merchant_context,
    run_get_settlement_entries,
)

client = TestClient(app)


@pytest.mark.asyncio
async def test_p3_a1_investigation_tools_direct() -> None:
    """Test the 4 investigation tools directly with database session."""
    async with shared_session_factory() as session:
        # Reset and seed the frozen scenario
        await reset_and_seed(session)

        ctx = ToolContext(merchant_id=MERCHANT_ID, session=session)

        # 1. get_merchant_context
        ctx_out = await run_get_merchant_context(GetMerchantContextInput(), ctx)
        assert ctx_out.display_name == "Two Bits Chai & Snacks"
        assert ctx_out.status == "ACTIVE"
        assert ctx_out.source_type == "SYNTHETIC_DEMO"

        # 2. find_transactions (retrieves 3 captured transactions totaling ₹15,000)
        txn_out = await run_find_transactions(FindTransactionsInput(), ctx)
        assert len(txn_out.transactions) == 3
        total_captured = sum(t.amount for t in txn_out.transactions)
        assert total_captured == Decimal("15000.00")
        assert len(txn_out.source_ids) == 3

        # 2b. find_transactions with specific amount filter (₹6,000)
        txn_filtered = await run_find_transactions(
            FindTransactionsInput(amount=Decimal("6000.00")), ctx
        )
        assert len(txn_filtered.transactions) == 1
        assert txn_filtered.transactions[0].amount == Decimal("6000.00")
        assert txn_filtered.transactions[0].provider_txn_id == "TXN_78456321"

        # 3. get_settlement_entries (retrieves 2 entries totaling ₹9,000)
        stl_out = await run_get_settlement_entries(
            GetSettlementEntriesInput(batch_ref="BATCH_20261112_01"), ctx
        )
        assert len(stl_out.entries) == 2
        total_settled = sum(e.amount for e in stl_out.entries)
        assert total_settled == Decimal("9000.00")

        # 4. calculate_discrepancy (computes ₹15,000 - ₹9,000 = ₹6,000 OVERDUE)
        calc_out = await run_calculate_discrepancy(
            CalculateDiscrepancyInput(
                transaction_ids=txn_out.source_ids,
                settlement_entry_ids=stl_out.source_ids,
            ),
            ctx,
        )
        assert calc_out.expected_net == Decimal("15000.00")
        assert calc_out.observed == Decimal("9000.00")
        assert calc_out.discrepancy == Decimal("6000.00")
        assert calc_out.reason_code == "OVERDUE"
        assert "expected_settlement_date" in calc_out.trace
        assert len(calc_out.source_ids) > 0


def test_p3_a1_golden_investigation_workflow_english() -> None:
    """Acceptance test: 'My ₹6,000 payment is missing' returns exact numbers and OVERDUE."""
    res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={
            "message": "My ₹6,000 payment from yesterday is missing from settlement",
            "language": "en",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    data = body["data"]

    # Verify intent and case
    assert data["intent"] == "SETTLEMENT_MISMATCH"
    assert data["active_case_id"] is not None

    # Verify evidence summary exact numbers and source labels
    evidence = data["evidence_summary"]
    assert evidence is not None
    assert evidence["expected_net"] == "15000.00"
    assert evidence["observed_net"] == "9000.00"
    assert evidence["discrepancy"] == "6000.00"
    assert evidence["reason_code"] == "OVERDUE"
    assert evidence["source_type"] == "SYNTHETIC_DEMO"

    # Verify merchant reply mentions the discrepancy
    reply = data["reply"]
    assert "6000" in reply or "₹6,000" in reply
    assert "investigated" in reply.lower() or "settlement" in reply.lower()


def test_p3_a1_investigation_multilingual_hindi() -> None:
    """Test investigation workflow with Hindi complaint."""
    res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={
            "message": "मेरा ₹6,000 का सेटलमेंट नहीं आया है",
            "language": "hi",
        },
    )
    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    assert data["language"] == "hi"
    assert data["evidence_summary"]["discrepancy"] == "6000.00"
    assert data["evidence_summary"]["reason_code"] == "OVERDUE"
    # Hindi reply verification
    reply = data["reply"]
    assert "₹6000.00" in reply or "6000" in reply
    assert "सेटलमेंट" in reply


def test_p3_a1_investigation_multilingual_marathi() -> None:
    """Test investigation workflow with Marathi complaint."""
    res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={
            "message": "माझे ₹६,००० चे पेमेंट सेटलमेंटमध्ये जमा झालेले नाही",
            "language": "mr",
        },
    )
    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    assert data["language"] == "mr"
    assert data["evidence_summary"]["discrepancy"] == "6000.00"
    assert data["evidence_summary"]["reason_code"] == "OVERDUE"
    # Marathi reply verification
    reply = data["reply"]
    assert "सेटलमेंट" in reply or "नोंदी" in reply
