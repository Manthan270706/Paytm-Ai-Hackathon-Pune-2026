import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentRun,
    Approval,
    AuditEvent,
    CaseEvent,
    Conversation,
    FeeRule,
    FollowupJob,
    Merchant,
    MerchantUser,
    Message,
    ResyncRequest,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    ToolExecution,
    Transaction,
    User,
    WebhookEvent,
)

# ------------------------------------------------------------------------------
# Fixed Deterministic Identifiers for the Golden Demo Scenario
# ------------------------------------------------------------------------------
MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MERCHANT_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
SUPPORT_USER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
SUPERVISOR_USER_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
FEE_RULE_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
BATCH_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")

TXN_1_ID = uuid.UUID("77777777-7777-7777-7777-777777777771")
TXN_2_ID = uuid.UUID("77777777-7777-7777-7777-777777777772")
TXN_3_ID = uuid.UUID("77777777-7777-7777-7777-777777777773")  # Missing ₹6,000 payment

ENTRY_1_ID = uuid.UUID("88888888-8888-8888-8888-888888888881")
ENTRY_2_ID = uuid.UUID("88888888-8888-8888-8888-888888888882")
SIMULATED_ENTRY_ID = uuid.UUID("88888888-8888-8888-8888-888888888883")

CASE_1_ID = uuid.UUID("99999999-9999-9999-9999-999999999991")
CASE_2_ID = uuid.UUID("99999999-9999-9999-9999-999999999992")
CASE_3_ID = uuid.UUID("99999999-9999-9999-9999-999999999993")
CASE_4_ID = uuid.UUID("99999999-9999-9999-9999-999999999994")
CASE_5_ID = uuid.UUID("99999999-9999-9999-9999-999999999995")

APPROVAL_1_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
APPROVAL_5_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


async def reset_and_seed(session: AsyncSession) -> dict[str, Any]:
    """Wipe demo tables and seed the exact frozen ₹15,000 / ₹9,000 / ₹6,000 scenario.

    Guarantees deterministic, reproducible state across tests, demos, and judging.
    """
    # 1. Clean existing records in reverse dependency order
    tables_to_clean = [
        AuditEvent,
        WebhookEvent,
        ToolExecution,
        AgentRun,
        FollowupJob,
        ResyncRequest,
        Approval,
        CaseEvent,
        Message,
        Conversation,
        SupportCase,
        SettlementEntry,
        SettlementBatch,
        Transaction,
        FeeRule,
        MerchantUser,
        Merchant,
        User,
    ]
    for table in tables_to_clean:
        await session.execute(delete(table))

    # 2. Seed Users
    merchant_user = User(
        id=MERCHANT_USER_ID,
        email="merchant@two-bits.demo",
        hashed_password="DEMO_HASH",
        role="MERCHANT",
        is_active=True,
        preferred_language="en",
    )
    support_user = User(
        id=SUPPORT_USER_ID,
        email="support@paytm.demo",
        hashed_password="DEMO_HASH",
        role="SUPPORT_AGENT",
        is_active=True,
        preferred_language="en",
    )
    supervisor_user = User(
        id=SUPERVISOR_USER_ID,
        email="supervisor@paytm.demo",
        hashed_password="DEMO_HASH",
        role="SUPERVISOR",
        is_active=True,
        preferred_language="en",
    )
    session.add_all([merchant_user, support_user, supervisor_user])

    # 3. Seed Merchant Profile
    merchant = Merchant(
        id=MERCHANT_ID,
        external_mid="MID_DEMO_TWOBITS",
        display_name="Paytm Smart Merchant Store",
        masked_phone="+91-98765-43210",
        status="ACTIVE",
    )
    session.add(merchant)
    await session.flush()

    # 4. Link Merchant and User
    membership = MerchantUser(
        user_id=MERCHANT_USER_ID,
        merchant_id=MERCHANT_ID,
        role="OWNER",
    )
    session.add(membership)
    await session.flush()

    # 5. Seed Documented Fee Rule (0% and ₹0 flat)
    fee_rule = FeeRule(
        id=FEE_RULE_ID,
        merchant_id=MERCHANT_ID,
        rule_ref="RULE_DEFAULT_2026",
        rate_percent=Decimal("0.00"),
        flat_amount=Decimal("0.00"),
        active=True,
        source_type="SYNTHETIC_DEMO",
    )
    session.add(fee_rule)

    # 6. Seed Successful Transactions (Total = ₹15,000)
    # Txn 1: ₹5,000 (captured in batch)
    txn_1 = Transaction(
        id=TXN_1_ID,
        merchant_id=MERCHANT_ID,
        provider="PAYTM",
        provider_txn_id="TXN_78456319",
        order_id="ORD_20261112_01",
        amount=Decimal("5000.00"),
        currency="INR",
        status="SUCCESS",
        txn_time=datetime(2026, 11, 12, 10, 15, tzinfo=UTC),
        source_type="SYNTHETIC_DEMO",
    )
    # Txn 2: ₹4,000 (captured in batch)
    txn_2 = Transaction(
        id=TXN_2_ID,
        merchant_id=MERCHANT_ID,
        provider="PAYTM",
        provider_txn_id="TXN_78456320",
        order_id="ORD_20261112_02",
        amount=Decimal("4000.00"),
        currency="INR",
        status="SUCCESS",
        txn_time=datetime(2026, 11, 12, 12, 45, tzinfo=UTC),
        source_type="SYNTHETIC_DEMO",
    )
    # Txn 3: ₹6,000 (missing from batch - the discrepancy!)
    txn_3 = Transaction(
        id=TXN_3_ID,
        merchant_id=MERCHANT_ID,
        provider="PAYTM",
        provider_txn_id="TXN_78456321",
        order_id="ORD_20261112_03",
        amount=Decimal("6000.00"),
        currency="INR",
        status="SUCCESS",
        txn_time=datetime(2026, 11, 12, 16, 20, tzinfo=UTC),
        source_type="SYNTHETIC_DEMO",
    )
    session.add_all([txn_1, txn_2, txn_3])
    await session.flush()

    # 7. Seed Settlement Batch (Observed = ₹9,000, Expected settlement date in the past)
    batch = SettlementBatch(
        id=BATCH_ID,
        merchant_id=MERCHANT_ID,
        batch_ref="BATCH_20261112_01",
        date=date(2026, 11, 12),
        expected_settlement_date=datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
        gross=Decimal("9000.00"),
        fees=Decimal("0.00"),
        refunds=Decimal("0.00"),
        net=Decimal("9000.00"),
        status="SETTLED",
        source_type="SYNTHETIC_DEMO",
    )
    session.add(batch)
    await session.flush()

    # 8. Seed Settlement Entries (Only Txn 1 and Txn 2 are present)
    entry_1 = SettlementEntry(
        id=ENTRY_1_ID,
        batch_id=BATCH_ID,
        transaction_id=TXN_1_ID,
        amount=Decimal("5000.00"),
        entry_type="CAPTURE",
        status="SETTLED",
        source_type="SYNTHETIC_DEMO",
    )
    entry_2 = SettlementEntry(
        id=ENTRY_2_ID,
        batch_id=BATCH_ID,
        transaction_id=TXN_2_ID,
        amount=Decimal("4000.00"),
        entry_type="CAPTURE",
        status="SETTLED",
        source_type="SYNTHETIC_DEMO",
    )
    session.add_all([entry_1, entry_2])

    # 9. Seed Multi-Case Operations Portfolio (PRD Track 3 Gated & Cross-Queue Scenarios)
    now = datetime.now(UTC)

    # Case 1: Golden ₹6,000 Overdue Settlement Mismatch (Settlement Ops, Awaiting Approval)
    case_1 = SupportCase(
        id=CASE_1_ID,
        merchant_id=MERCHANT_ID,
        case_number="CASE-2026-1024",
        category="SETTLEMENT_MISMATCH",
        priority="P1",
        status="AWAITING_APPROVAL",
        queue="SETTLEMENT_OPS",
        summary="Missing ₹6,000 from settlement batch BATCH_20261112_01",
        idempotency_key=f"IDEMP-CASE-{MERCHANT_ID}-6000.00",
        version=1,
        created_at=now - timedelta(hours=24),
        updated_at=now - timedelta(hours=24),
    )
    ev_1_1 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_1_ID,
        actor="merchant@two-bits.demo",
        event_type="CASE_CREATED",
        from_status=None,
        to_status="NEW",
        visibility="MERCHANT",
        payload={"category": "SETTLEMENT_MISMATCH", "summary": "Missing ₹6,000 from settlement batch BATCH_20261112_01"},
        created_at=now - timedelta(hours=24),
    )
    ev_1_2 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_1_ID,
        actor="OpsSaathi AI",
        event_type="EVIDENCE_ATTACHED",
        from_status="NEW",
        to_status="INVESTIGATING",
        visibility="INTERNAL",
        payload={
            "expected_net": "15000.00",
            "observed_net": "9000.00",
            "discrepancy": "6000.00",
            "reason_code": "OVERDUE",
            "batch_ref": "BATCH_20261112_01",
        },
        created_at=now - timedelta(hours=23, minutes=58),
    )
    ev_1_3 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_1_ID,
        actor="OpsSaathi PolicyEngine",
        event_type="GATED_POLICY_TRIGGERED",
        from_status="INVESTIGATING",
        to_status="AWAITING_APPROVAL",
        visibility="INTERNAL",
        payload={
            "policy_rule": "Policy Rule #3",
            "threshold": "5000.00",
            "discrepancy": "6000.00",
            "decision": "REQUIRE_HUMAN_APPROVAL",
        },
        created_at=now - timedelta(hours=23, minutes=55),
    )
    appr_1 = Approval(
        id=APPROVAL_1_ID,
        case_id=CASE_1_ID,
        action="SETTLEMENT_RESYNC",
        case_version=1,
        action_hash="44efa879046efa3a441c61673e778f5ed3cb2adec16c9d57ca0f88b6139a2e02",
        status="ACTIVE",
        decision="PENDING",
        created_at=now - timedelta(hours=23, minutes=55),
    )

    # Case 2: Customer Refund Double Debit (Settlements Queue, In Progress)
    case_2 = SupportCase(
        id=CASE_2_ID,
        merchant_id=MERCHANT_ID,
        case_number="CASE-2026-1025",
        category="REFUND_DISPUTE",
        priority="P2",
        status="IN_PROGRESS",
        queue="SETTLEMENTS",
        summary="Customer refund for Order #ORD_20261111_09 debited twice (₹1,200.00) on ledger",
        idempotency_key=f"IDEMP-CASE-{MERCHANT_ID}-1200.00",
        version=1,
        created_at=now - timedelta(hours=18),
        updated_at=now - timedelta(hours=18),
    )
    ev_2_1 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_2_ID,
        actor="merchant@two-bits.demo",
        event_type="CASE_CREATED",
        from_status=None,
        to_status="NEW",
        visibility="MERCHANT",
        payload={"category": "REFUND_DISPUTE", "summary": "Customer refund for Order #ORD_20261111_09 debited twice (₹1,200.00) on ledger"},
        created_at=now - timedelta(hours=18),
    )
    ev_2_2 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_2_ID,
        actor="OpsSaathi AI",
        event_type="LEDGER_AUDIT_MATCHED",
        from_status="NEW",
        to_status="IN_PROGRESS",
        visibility="INTERNAL",
        payload={"order_id": "ORD_20261111_09", "duplicate_debit": "1200.00", "original_txn_id": "TXN_78456319"},
        created_at=now - timedelta(hours=17, minutes=50),
    )
    ev_2_3 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_2_ID,
        actor="OpsSaathi AI",
        event_type="REFUND_CLAWBACK_QUEUED",
        from_status="IN_PROGRESS",
        to_status="IN_PROGRESS",
        visibility="MERCHANT",
        payload={"adjustment_type": "CREDIT_REVERSAL", "queue": "SETTLEMENTS", "status": "QUEUED"},
        created_at=now - timedelta(hours=17, minutes=45),
    )

    # Case 3: MDR Commission Rate Overcharge (Settlement Ops Queue, Verifying)
    case_3 = SupportCase(
        id=CASE_3_ID,
        merchant_id=MERCHANT_ID,
        case_number="CASE-2026-1026",
        category="FEE_OVERCHARGE",
        priority="P2",
        status="VERIFYING",
        queue="SETTLEMENT_OPS",
        summary="MDR fee rate mismatch: 2.15% charged on RuPay batch instead of agreed 1.20% (₹850.00 diff)",
        idempotency_key=f"IDEMP-CASE-{MERCHANT_ID}-850.00",
        version=2,
        created_at=now - timedelta(hours=12),
        updated_at=now - timedelta(hours=12),
    )
    ev_3_1 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_3_ID,
        actor="merchant@two-bits.demo",
        event_type="CASE_CREATED",
        from_status=None,
        to_status="NEW",
        visibility="MERCHANT",
        payload={"category": "FEE_OVERCHARGE", "summary": "MDR fee rate mismatch: 2.15% charged on RuPay batch instead of agreed 1.20% (₹850.00 diff)"},
        created_at=now - timedelta(hours=12),
    )
    ev_3_2 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_3_ID,
        actor="OpsSaathi AI",
        event_type="FEE_SCHEDULE_AUDITED",
        from_status="NEW",
        to_status="IN_PROGRESS",
        visibility="INTERNAL",
        payload={"rate_billed": "2.15%", "contract_rate": "1.20%", "variance": "850.00"},
        created_at=now - timedelta(hours=11, minutes=50),
    )
    ev_3_3 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_3_ID,
        actor="supervisor@paytm.demo",
        event_type="APPROVAL_GRANTED",
        from_status="IN_PROGRESS",
        to_status="APPROVED",
        visibility="INTERNAL",
        payload={"credit_note": "CN-20261112-0850", "approved_amount": "850.00"},
        created_at=now - timedelta(hours=10),
    )
    ev_3_4 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_3_ID,
        actor="OpsSaathi AI",
        event_type="CREDIT_ADJUSTMENT_POSTED",
        from_status="APPROVED",
        to_status="VERIFYING",
        visibility="MERCHANT",
        payload={"credit_note": "CN-20261112-0850", "amount": "850.00", "status": "APPLIED"},
        created_at=now - timedelta(hours=9, minutes=50),
    )

    # Case 4: Soundbox Hardware Diagnostics (Tech Support Queue, Resolved)
    case_4 = SupportCase(
        id=CASE_4_ID,
        merchant_id=MERCHANT_ID,
        case_number="CASE-2026-1027",
        category="HARDWARE_DIAGNOSTICS",
        priority="P3",
        status="RESOLVED",
        queue="TECH_SUPPORT",
        summary="Paytm Soundbox 4G audio announcement delayed by 45s during morning rush",
        idempotency_key=f"IDEMP-CASE-{MERCHANT_ID}-SOUNDBOX-01",
        version=3,
        created_at=now - timedelta(hours=8),
        updated_at=now - timedelta(hours=8),
    )
    ev_4_1 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_4_ID,
        actor="merchant@two-bits.demo",
        event_type="CASE_CREATED",
        from_status=None,
        to_status="NEW",
        visibility="MERCHANT",
        payload={"category": "HARDWARE_DIAGNOSTICS", "summary": "Paytm Soundbox 4G audio announcement delayed by 45s during morning rush"},
        created_at=now - timedelta(hours=8),
    )
    ev_4_2 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_4_ID,
        actor="OpsSaathi AI",
        event_type="TELEMETRY_DIAGNOSED",
        from_status="NEW",
        to_status="IN_PROGRESS",
        visibility="INTERNAL",
        payload={"device_imei": "860459048123456", "signal_rsrp": "-82dBm", "cell_status": "EXCELLENT", "firmware_version": "v4.2.1-prod"},
        created_at=now - timedelta(hours=7, minutes=45),
    )
    ev_4_3 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_4_ID,
        actor="OpsSaathi AI",
        event_type="FIRMWARE_CACHE_FLUSHED",
        from_status="IN_PROGRESS",
        to_status="VERIFYING",
        visibility="MERCHANT",
        payload={"action": "REMOTE_CACHE_PURGE", "result": "SUCCESS", "audio_latency_ms": 320},
        created_at=now - timedelta(hours=7, minutes=30),
    )
    ev_4_4 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_4_ID,
        actor="opssaathi_verifier",
        event_type="VERIFICATION_COMPLETED",
        from_status="VERIFYING",
        to_status="RESOLVED",
        visibility="MERCHANT",
        payload={"verification_result": "PASS", "verifier_role": "opssaathi_verifier", "test_chime": "CONFIRMED"},
        created_at=now - timedelta(hours=7),
    )
    ev_4_5 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_4_ID,
        actor="opssaathi_verifier",
        event_type="CASE_RESOLVED",
        from_status="VERIFYING",
        to_status="RESOLVED",
        visibility="MERCHANT",
        payload={"status": "RESOLVED", "resolved_by": "OpsSaathi AI"},
        created_at=now - timedelta(hours=7),
    )

    # Case 5: Weekend Bank Holiday Payout Hold (Escalations Queue, High Priority P0)
    case_5 = SupportCase(
        id=CASE_5_ID,
        merchant_id=MERCHANT_ID,
        case_number="CASE-2026-1028",
        category="PAYOUT_DELAY",
        priority="P0",
        status="AWAITING_APPROVAL",
        queue="SETTLEMENTS",
        summary="T+1 bank holiday hold exceeded 48h SLA for weekend batch BATCH_20261110_02 (₹18,500.00)",
        idempotency_key=f"IDEMP-CASE-{MERCHANT_ID}-18500.00",
        version=1,
        created_at=now - timedelta(hours=4),
        updated_at=now - timedelta(hours=4),
    )
    ev_5_1 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_5_ID,
        actor="merchant@two-bits.demo",
        event_type="CASE_CREATED",
        from_status=None,
        to_status="NEW",
        visibility="MERCHANT",
        payload={"category": "PAYOUT_DELAY", "summary": "T+1 bank holiday hold exceeded 48h SLA for weekend batch BATCH_20261110_02 (₹18,500.00)"},
        created_at=now - timedelta(hours=4),
    )
    ev_5_2 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_5_ID,
        actor="OpsSaathi AI",
        event_type="SLA_BREACH_DETECTED",
        from_status="NEW",
        to_status="IN_PROGRESS",
        visibility="INTERNAL",
        payload={"batch_ref": "BATCH_20261110_02", "amount": "18500.00", "sla_hours_elapsed": 52, "bank_utr": "PBNK20261110998811"},
        created_at=now - timedelta(hours=3, minutes=45),
    )
    ev_5_3 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_5_ID,
        actor="OpsSaathi AI",
        event_type="ESCALATED_TIER_2",
        from_status="IN_PROGRESS",
        to_status="AWAITING_APPROVAL",
        visibility="INTERNAL",
        payload={"escalated_to": "ESCALATIONS", "assigned_role": "SUPERVISOR", "priority": "P0"},
        created_at=now - timedelta(hours=3, minutes=30),
    )
    ev_5_4 = CaseEvent(
        id=uuid.uuid4(),
        case_id=CASE_5_ID,
        actor="OpsSaathi PolicyEngine",
        event_type="GATED_POLICY_TRIGGERED",
        from_status="AWAITING_APPROVAL",
        to_status="AWAITING_APPROVAL",
        visibility="INTERNAL",
        payload={"policy_rule": "Rule #3 High-Value Wire Release", "threshold": "5000.00", "amount": "18500.00", "decision": "REQUIRE_HUMAN_APPROVAL"},
        created_at=now - timedelta(hours=3, minutes=25),
    )
    appr_5 = Approval(
        id=APPROVAL_5_ID,
        case_id=CASE_5_ID,
        action="EXPEDITED_WIRE_RELEASE",
        case_version=1,
        action_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        status="ACTIVE",
        decision="PENDING",
        created_at=now - timedelta(hours=3, minutes=25),
    )

    session.add_all([
        case_1, ev_1_1, ev_1_2, ev_1_3, appr_1,
        case_2, ev_2_1, ev_2_2, ev_2_3,
        case_3, ev_3_1, ev_3_2, ev_3_3, ev_3_4,
        case_4, ev_4_1, ev_4_2, ev_4_3, ev_4_4, ev_4_5,
        case_5, ev_5_1, ev_5_2, ev_5_3, ev_5_4, appr_5,
    ])

    await session.commit()

    return {
        "merchant_id": MERCHANT_ID,
        "batch_ref": "BATCH_20261112_01",
        "expected_net": Decimal("15000.00"),
        "observed_net": Decimal("9000.00"),
        "discrepancy": Decimal("6000.00"),
        "reason_code": "OVERDUE",
        "missing_txn_id": "TXN_78456321",
        "missing_order_id": "ORD_20261112_03",
    }


async def simulate_bank_settlement(
    session: AsyncSession, merchant_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """Simulate bank-side settlement credit for the missing ₹6,000 transaction.

    Inserts the missing SettlementEntry and updates SettlementBatch net to ₹15,000.00.
    Labelled strictly as SYNTHETIC_DEMO.
    """
    target_merchant_id = merchant_id or MERCHANT_ID

    # Check if simulated entry is already added
    stmt = select(SettlementEntry).where(SettlementEntry.id == SIMULATED_ENTRY_ID)
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if not existing:
        entry_3 = SettlementEntry(
            id=SIMULATED_ENTRY_ID,
            batch_id=BATCH_ID,
            transaction_id=TXN_3_ID,
            amount=Decimal("6000.00"),
            entry_type="CAPTURE",
            status="SETTLED",
            source_type="SYNTHETIC_DEMO",
        )
        session.add(entry_3)

        # Update batch totals
        batch_stmt = select(SettlementBatch).where(SettlementBatch.id == BATCH_ID)
        batch = (await session.execute(batch_stmt)).scalar_one_or_none()
        if batch:
            batch.gross = Decimal("15000.00")
            batch.net = Decimal("15000.00")

        # Record audit event
        audit = AuditEvent(
            actor="SYSTEM_DEMO_SIMULATOR",
            action="SIMULATE_BANK_SETTLEMENT",
            resource=f"settlement_batches/{BATCH_ID}",
            trace_id=f"trace_sim_{uuid.uuid4().hex[:12]}",
            payload={
                "merchant_id": str(target_merchant_id),
                "added_amount": "6000.00",
                "new_net": "15000.00",
                "source_type": "SYNTHETIC_DEMO",
            },
        )
        session.add(audit)
        await session.commit()

    return {
        "status": "APPLIED",
        "entry_id": SIMULATED_ENTRY_ID,
        "amount": Decimal("6000.00"),
        "new_observed_net": Decimal("15000.00"),
        "source_type": "SYNTHETIC_DEMO",
    }
