import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import SettlementBatchResponse, SettlementEntryResponse
from app.core.dependencies import AuthContext, get_auth_context
from app.core.response import success_response
from app.db.models import SettlementBatch, SettlementEntry, Transaction
from app.db.session import get_db_session

router = APIRouter()


@router.get("/settlements", summary="Return settlement batches and entries")
async def list_settlements(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    # Query batches strictly scoped to current merchant
    batch_stmt = select(SettlementBatch).where(
        SettlementBatch.merchant_id == auth.active_merchant_id
    )
    batches = list((await session.execute(batch_stmt)).scalars().all())

    if not batches:
        # Fallback demo batch representation if DB unseeded
        mock_batch_id = uuid.uuid4()
        batch = SettlementBatchResponse(
            id=mock_batch_id,
            merchant_id=auth.active_merchant_id,
            batch_ref="BATCH_20261112_01",
            date=date(2026, 11, 12),
            expected_settlement_date=datetime.now(UTC),
            gross=Decimal("9000.00"),
            fees=Decimal("0.00"),
            refunds=Decimal("0.00"),
            net=Decimal("9000.00"),
            status="SETTLED",
            source_type="SYNTHETIC_DEMO",
            entries_count=2,
        )
        return success_response(
            data={
                "batches": [batch.model_dump()],
                "entries": [],
                "discrepancy_amount": Decimal("6000.00"),
                "reason_code": "OVERDUE",
            },
            source_type="SYNTHETIC_DEMO",
        )

    # Fetch entries for all merchant batches
    batch_ids = [b.id for b in batches]
    entry_stmt = select(SettlementEntry).where(SettlementEntry.batch_id.in_(batch_ids))
    entries = list((await session.execute(entry_stmt)).scalars().all())

    # Calculate discrepancy against successful transactions
    txn_stmt = select(Transaction).where(
        Transaction.merchant_id == auth.active_merchant_id,
        Transaction.status == "SUCCESS",
    )
    successful_txns = list((await session.execute(txn_stmt)).scalars().all())
    expected_net = sum((t.amount for t in successful_txns), Decimal("0.00"))
    observed_net = sum((b.net for b in batches), Decimal("0.00"))
    discrepancy = max(Decimal("0.00"), expected_net - observed_net)

    batch_responses = [
        SettlementBatchResponse(
            id=b.id,
            merchant_id=b.merchant_id,
            batch_ref=b.batch_ref,
            date=b.date,
            expected_settlement_date=b.expected_settlement_date,
            gross=b.gross,
            fees=b.fees,
            refunds=b.refunds,
            net=b.net,
            status=b.status,
            source_type=b.source_type,
            entries_count=len([e for e in entries if e.batch_id == b.id]),
        ).model_dump()
        for b in batches
    ]

    entry_responses = [
        SettlementEntryResponse(
            id=e.id,
            batch_id=e.batch_id,
            transaction_id=e.transaction_id,
            amount=e.amount,
            entry_type=e.entry_type,
            status=e.status,
            source_type=e.source_type,
            created_at=datetime.now(UTC),
        ).model_dump()
        for e in entries
    ]

    return success_response(
        data={
            "batches": batch_responses,
            "entries": entry_responses,
            "discrepancy_amount": discrepancy,
            "reason_code": "OVERDUE" if discrepancy > Decimal("0.00") else "NO_DISCREPANCY",
        },
        source_type="SYNTHETIC_DEMO",
    )
