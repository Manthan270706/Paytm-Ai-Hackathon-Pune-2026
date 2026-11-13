import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
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


async def reset_and_seed(session: AsyncSession) -> dict[str, Any]:
    """Wipe demo tables and seed the exact frozen ₹15,000 / ₹9,000 / ₹6,000 scenario.

    Guarantees deterministic, reproducible state across tests, demos, and judging.
    """
    # 1. Clean existing records in reverse dependency order
    tables_to_clean = [
        AuditEvent,
        WebhookEvent,
        ToolExecution,
        FollowupJob,
        ResyncRequest,
        Approval,
        CaseEvent,
        SupportCase,
        Message,
        Conversation,
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
        hashed_password="mock_hashed_password_demo123",
        role="MERCHANT",
        is_active=True,
        preferred_language="en",
    )
    support_user = User(
        id=SUPPORT_USER_ID,
        email="support@paytm.demo",
        hashed_password="mock_hashed_password_demo123",
        role="SUPPORT_AGENT",
        is_active=True,
        preferred_language="en",
    )
    supervisor_user = User(
        id=SUPERVISOR_USER_ID,
        email="supervisor@paytm.demo",
        hashed_password="mock_hashed_password_demo123",
        role="SUPERVISOR",
        is_active=True,
        preferred_language="en",
    )
    session.add_all([merchant_user, support_user, supervisor_user])

    # 3. Seed Merchant Profile
    merchant = Merchant(
        id=MERCHANT_ID,
        external_mid="MID_DEMO_TWOBITS",
        display_name="Two Bits Chai & Snacks",
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
