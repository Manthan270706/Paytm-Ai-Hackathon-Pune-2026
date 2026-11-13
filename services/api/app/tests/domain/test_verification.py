import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ForbiddenError, ValidationError
from app.db.base import Base
from app.db.models import (
    CaseEvent,
    FeeRule,
    Merchant,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    Transaction,
)
from app.db.session import _create_engine
from app.domain.case_lifecycle import transition
from app.domain.verification import VerificationResult, verify_resolution


@pytest_asyncio.fixture
async def db_factory(
    tmp_path: Path,
) -> AsyncGenerator[tuple[async_sessionmaker[AsyncSession], str], None]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'verification.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False), database_url
    await engine.dispose()


async def _seed_scenario(
    session: AsyncSession,
    *,
    observed: Decimal,
    with_before_event: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    merchant_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    case_id = uuid.uuid4()
    batch_ref = "BATCH-VERIFY-01"
    now = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    session.add_all(
        [
            Merchant(id=merchant_id, display_name="Demo merchant", masked_phone="******1234"),
            SettlementBatch(
                id=batch_id,
                merchant_id=merchant_id,
                batch_ref=batch_ref,
                date=date(2026, 11, 12),
                expected_settlement_date=datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
                gross=observed,
                fees=Decimal("0.00"),
                refunds=Decimal("0.00"),
                net=observed,
                status="SETTLED",
                source_type="SYNTHETIC_DEMO",
            ),
            SupportCase(
                id=case_id,
                merchant_id=merchant_id,
                case_number="CASE-VERIFY-01",
                category="SETTLEMENT_MISMATCH",
                status="VERIFYING",
                summary="Settlement verification",
                idempotency_key=f"verify-{case_id}",
                version=4,
            ),
            FeeRule(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                rule_ref="zero-fee",
                rate_percent=Decimal("0.00"),
                flat_amount=Decimal("0.00"),
                active=True,
                source_type="SYNTHETIC_DEMO",
            ),
        ]
    )

    transaction_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    session.add_all(
        [
            Transaction(
                id=transaction_id,
                merchant_id=merchant_id,
                provider_txn_id=f"provider-{index}",
                order_id=f"order-{index}",
                amount=amount,
                currency="INR",
                status="SUCCESS",
                txn_time=datetime(2026, 11, 12, 10 + index, 0, tzinfo=UTC),
                source_type="SYNTHETIC_DEMO",
            )
            for index, (transaction_id, amount) in enumerate(
                zip(
                    transaction_ids,
                    (Decimal("5000.00"), Decimal("4000.00"), Decimal("6000.00")),
                    strict=True,
                )
            )
        ]
    )
    entry_amounts = (Decimal("5000.00"), Decimal("4000.00"), Decimal("6000.00"))
    observed_remaining = observed
    entries: list[SettlementEntry] = []
    for transaction_id, amount in zip(transaction_ids, entry_amounts, strict=True):
        if observed_remaining <= 0:
            break
        credited = min(observed_remaining, amount)
        entries.append(
            SettlementEntry(
                id=uuid.uuid4(),
                batch_id=batch_id,
                transaction_id=transaction_id,
                amount=credited,
                entry_type="CAPTURE",
                status="SETTLED",
                source_type="SYNTHETIC_DEMO",
            )
        )
        observed_remaining -= credited
    session.add_all(entries)

    if with_before_event:
        session.add(
            CaseEvent(
                id=uuid.uuid4(),
                case_id=case_id,
                actor="OpsSaathi AI",
                event_type="INVESTIGATION_COMPLETED",
                visibility="INTERNAL",
                payload={
                    "batch_ref": batch_ref,
                    "reconciliation": {
                        "expected_net": "15000.00",
                        "observed": "9000.00",
                    },
                },
                created_at=now,
            )
        )
    await session.flush()
    return case_id, batch_id, merchant_id


@pytest.mark.asyncio
async def test_verification_passes_only_when_fresh_observed_matches_expected(
    db_factory: tuple[async_sessionmaker[AsyncSession], str],
) -> None:
    factory, _ = db_factory
    async with factory() as session:
        case_id, _, _ = await _seed_scenario(session, observed=Decimal("15000.00"))
        await session.commit()

    now = datetime(2026, 11, 13, 13, 0, tzinfo=UTC)
    async with factory() as verifier_session:
        result = await verify_resolution(
            case_id, "RECONCILE_DISCREPANCY_ZERO", verifier_session, now
        )

    assert result == VerificationResult(
        status="PASS",
        before=Decimal("6000.00"),
        after=Decimal("0.00"),
        evidence_timestamp=now,
    )


@pytest.mark.asyncio
async def test_unchanged_ledger_fails_verification_and_cannot_close_case(
    db_factory: tuple[async_sessionmaker[AsyncSession], str],
) -> None:
    factory, _ = db_factory
    async with factory() as session:
        case_id, _, _ = await _seed_scenario(session, observed=Decimal("9000.00"))
        case = (
            await session.execute(select(SupportCase).where(SupportCase.id == case_id))
        ).scalar_one()
        await session.commit()

    now = datetime(2026, 11, 13, 13, 0, tzinfo=UTC)
    async with factory() as verifier_session:
        result = await verify_resolution(
            case_id, "RECONCILE_DISCREPANCY_ZERO", verifier_session, now
        )

    assert result.status == "FAIL"
    assert result.before == Decimal("6000.00")
    assert result.after == Decimal("6000.00")
    with pytest.raises(ForbiddenError, match="verification PASS"):
        transition(case, "RESOLVED", expected_version=4, actor="verifier")


@pytest.mark.asyncio
async def test_fresh_verifier_read_observes_settlement_added_after_stale_load(
    db_factory: tuple[async_sessionmaker[AsyncSession], str],
) -> None:
    factory, _ = db_factory
    async with factory() as session:
        case_id, batch_id, merchant_id = await _seed_scenario(
            session, observed=Decimal("9000.00")
        )
        await session.commit()

    async with factory() as verifier_session:
        stale_entries = list(
            (
                await verifier_session.execute(
                    select(SettlementEntry).where(SettlementEntry.batch_id == batch_id)
                )
            )
            .scalars()
            .all()
        )
        assert sum((entry.amount for entry in stale_entries), Decimal("0")) == Decimal("9000.00")

        async with factory() as writer:
            missing_txn = (
                await writer.execute(
                    select(Transaction).where(
                        Transaction.merchant_id == merchant_id,
                        Transaction.amount == Decimal("6000.00"),
                    )
                )
            ).scalar_one()
            writer.add(
                SettlementEntry(
                    id=uuid.uuid4(),
                    batch_id=batch_id,
                    transaction_id=missing_txn.id,
                    amount=Decimal("6000.00"),
                    entry_type="CAPTURE",
                    status="SETTLED",
                    source_type="SYNTHETIC_DEMO",
                )
            )
            await writer.commit()

        await verifier_session.rollback()
        result = await verify_resolution(
            case_id,
            "RECONCILE_DISCREPANCY_ZERO",
            verifier_session,
            datetime(2026, 11, 13, 14, 0, tzinfo=UTC),
        )

    assert result.status == "PASS"
    assert result.after == Decimal("0.00")


@pytest.mark.asyncio
async def test_verifier_database_session_is_read_only(
    db_factory: tuple[async_sessionmaker[AsyncSession], str],
) -> None:
    factory, database_url = db_factory
    async with factory() as session:
        case_id, _, _ = await _seed_scenario(session, observed=Decimal("15000.00"))
        await session.commit()

    verifier_engine = _create_engine(database_url, is_verifier=True)
    verifier_factory = async_sessionmaker(verifier_engine, expire_on_commit=False)
    async with verifier_factory() as verifier_session:
        result = await verify_resolution(
            case_id,
            "RECONCILE_DISCREPANCY_ZERO",
            verifier_session,
            datetime(2026, 11, 13, 15, 0, tzinfo=UTC),
        )
        assert result.status == "PASS"
        with pytest.raises(OperationalError):
            await verifier_session.execute(text("UPDATE settlement_batches SET status='OPEN'"))
    await verifier_engine.dispose()


@pytest.mark.asyncio
async def test_verification_requires_a_recorded_before_state(
    db_factory: tuple[async_sessionmaker[AsyncSession], str],
) -> None:
    factory, _ = db_factory
    async with factory() as session:
        case_id, _, _ = await _seed_scenario(
            session,
            observed=Decimal("15000.00"),
            with_before_event=False,
        )
        await session.commit()

    async with factory() as verifier_session:
        with pytest.raises(ValidationError, match="No recorded before-state"):
            await verify_resolution(
                case_id,
                "RECONCILE_DISCREPANCY_ZERO",
                verifier_session,
                datetime(2026, 11, 13, 16, 0, tzinfo=UTC),
            )
