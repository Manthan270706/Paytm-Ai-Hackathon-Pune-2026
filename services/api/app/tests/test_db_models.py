import os
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.base import Base
from app.db.models import (
    Merchant,
    SupportCase,
    Transaction,
    User,
)
from app.db.session import AsyncSession, _create_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_clean.db"


@pytest.fixture(scope="module")
async def test_db():
    engine = _create_engine(TEST_DB_URL, is_verifier=False)
    verifier_engine = _create_engine(TEST_DB_URL, is_verifier=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    verifier_session_maker = async_sessionmaker(
        bind=verifier_engine, class_=AsyncSession, expire_on_commit=False
    )

    yield session_maker, verifier_session_maker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    await verifier_engine.dispose()
    if os.path.exists("./test_clean.db"):
        os.remove("./test_clean.db")


@pytest.mark.asyncio
async def test_db_schema_and_inserts(test_db):
    session_maker, _ = test_db

    async with session_maker() as session:
        # Create user
        user = User(
            email="test_merchant@paytm.demo",
            hashed_password="hashed_pw_test",
            role="MERCHANT",
            is_active=True,
            preferred_language="en",
        )
        session.add(user)

        # Create merchant
        merchant = Merchant(
            external_mid="TEST_MID_12345",
            display_name="Ramesh Kirana Store",
            masked_phone="+91 98*** **321",
            status="ACTIVE",
        )
        session.add(merchant)
        await session.flush()

        # Create transaction with strict Decimal amount
        txn = Transaction(
            merchant_id=merchant.id,
            provider="PAYTM",
            provider_txn_id="TXN_TEST_999",
            order_id="ORD_TEST_999",
            amount=Decimal("6000.00"),
            currency="INR",
            status="SUCCESS",
            txn_time=datetime.now(UTC),
            source_type="SYNTHETIC_DEMO",
        )
        session.add(txn)

        # Create support case with versioning
        case = SupportCase(
            merchant_id=merchant.id,
            case_number="CASE-2026-0001",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="NEW",
            queue="SETTLEMENT_OPS",
            summary="Payment missing from settlement payout",
            idempotency_key="IDEMP-KEY-TEST-1",
            version=1,
        )
        session.add(case)
        await session.commit()

        # Query and assert Decimal precision and versioning
        result = await session.execute(
            select(Transaction).where(Transaction.order_id == "ORD_TEST_999")
        )
        queried_txn = result.scalar_one()
        assert queried_txn.amount == Decimal("6000.00")
        assert queried_txn.source_type == "SYNTHETIC_DEMO"

        case_res = await session.execute(
            select(SupportCase).where(SupportCase.case_number == "CASE-2026-0001")
        )
        queried_case = case_res.scalar_one()
        assert queried_case.version == 1
        assert queried_case.status == "NEW"


@pytest.mark.asyncio
async def test_verifier_role_cannot_insert(test_db):
    _, verifier_session_maker = test_db

    async with verifier_session_maker() as v_session:
        # Verifier CAN perform read operations
        read_res = await v_session.execute(select(Merchant))
        merchants = read_res.scalars().all()
        assert len(merchants) >= 1

        # Verifier CANNOT perform write operations (PRD §7.5 & BUILD_PLAN P1-A2)
        unauthorized_merchant = Merchant(
            external_mid="HACK_MID_000",
            display_name="Unauthorized Write Store",
            masked_phone="+91 00*** **000",
            status="ACTIVE",
        )
        v_session.add(unauthorized_merchant)

        with pytest.raises((OperationalError, DBAPIError)) as exc_info:
            await v_session.commit()

        # Ensure error clearly indicates read-only protection
        err_msg = str(exc_info.value).lower()
        assert (
            "readonly" in err_msg
            or "read-only" in err_msg
            or "permission" in err_msg
            or "denied" in err_msg
        )
