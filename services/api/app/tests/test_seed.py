from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.base import Base
from app.db.models import FeeRule, Merchant, SettlementBatch, SettlementEntry, Transaction, User
from app.db.seed import (
    BATCH_ID,
    MERCHANT_ID,
    reset_and_seed,
    simulate_bank_settlement,
)
from app.db.session import AsyncSession, _create_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_seed_clean.db"


@pytest.fixture(scope="module")
async def seed_test_db():
    engine = _create_engine(TEST_DB_URL, is_verifier=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield session_maker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_reset_and_seed_frozen_scenario(seed_test_db) -> None:
    session_maker = seed_test_db

    async with session_maker() as session:
        result = await reset_and_seed(session)

        # 1. Assert returned values match PRD §10.2 frozen contract exactly
        assert result["merchant_id"] == MERCHANT_ID
        assert result["expected_net"] == Decimal("15000.00")
        assert result["observed_net"] == Decimal("9000.00")
        assert result["discrepancy"] == Decimal("6000.00")
        assert result["reason_code"] == "OVERDUE"
        assert result["missing_txn_id"] == "TXN_78456321"
        assert result["missing_order_id"] == "ORD_20261112_03"

        # 2. Assert Users created
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 3
        emails = {u.email for u in users}
        assert "merchant@two-bits.demo" in emails
        assert "support@paytm.demo" in emails
        assert "supervisor@paytm.demo" in emails

        # 3. Assert Merchant Profile
        merchant = (
            await session.execute(select(Merchant).where(Merchant.id == MERCHANT_ID))
        ).scalar_one()
        assert merchant.display_name == "Two Bits Chai & Snacks"
        assert merchant.status == "ACTIVE"

        # 4. Assert Fee Rule (0% and 0 flat)
        fee_rules = (await session.execute(select(FeeRule))).scalars().all()
        assert len(fee_rules) == 1
        assert fee_rules[0].rate_percent == Decimal("0.00")
        assert fee_rules[0].flat_amount == Decimal("0.00")

        # 5. Assert Transactions (₹5,000 + ₹4,000 + ₹6,000 = ₹15,000)
        txns = (await session.execute(select(Transaction))).scalars().all()
        assert len(txns) == 3
        total_txns = sum(t.amount for t in txns)
        assert total_txns == Decimal("15000.00")

        # 6. Assert Settlement Batch and Entries (₹5,000 + ₹4,000 = ₹9,000)
        batch = (
            await session.execute(select(SettlementBatch).where(SettlementBatch.id == BATCH_ID))
        ).scalar_one()
        assert batch.net == Decimal("9000.00")
        assert batch.gross == Decimal("9000.00")

        entries = (
            (
                await session.execute(
                    select(SettlementEntry).where(SettlementEntry.batch_id == BATCH_ID)
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 2
        total_entries = sum(e.amount for e in entries)
        assert total_entries == Decimal("9000.00")


@pytest.mark.asyncio
async def test_simulate_bank_settlement(seed_test_db) -> None:
    session_maker = seed_test_db

    async with session_maker() as session:
        # Before simulation: net is 9,000
        sim_res = await simulate_bank_settlement(session)
        assert sim_res["amount"] == Decimal("6000.00")
        assert sim_res["new_observed_net"] == Decimal("15000.00")

        # Verify batch is updated to 15,000
        batch = (
            await session.execute(select(SettlementBatch).where(SettlementBatch.id == BATCH_ID))
        ).scalar_one()
        assert batch.net == Decimal("15000.00")

        # Verify 3 entries exist now
        entries = (
            (
                await session.execute(
                    select(SettlementEntry).where(SettlementEntry.batch_id == BATCH_ID)
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 3
        assert sum(e.amount for e in entries) == Decimal("15000.00")


@pytest.mark.asyncio
async def test_reset_reproducibility(seed_test_db) -> None:
    session_maker = seed_test_db

    async with session_maker() as session:
        # Reset again after simulation
        result = await reset_and_seed(session)
        assert result["expected_net"] == Decimal("15000.00")
        assert result["observed_net"] == Decimal("9000.00")
        assert result["discrepancy"] == Decimal("6000.00")

        # Verify entries back to 2
        entries = (
            (
                await session.execute(
                    select(SettlementEntry).where(SettlementEntry.batch_id == BATCH_ID)
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 2
