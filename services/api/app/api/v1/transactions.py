import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import TransactionDetailResponse, TransactionItemResponse
from app.core.dependencies import AuthContext, get_auth_context, get_scoped_repo
from app.core.exceptions import NotFoundError
from app.core.response import success_response
from app.db.models import SettlementEntry, Transaction
from app.db.scoped_repository import ScopedRepository
from app.db.session import get_db_session

router = APIRouter()


@router.get("/transactions", summary="Tenant-scoped transaction search")
async def list_transactions(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    scoped_repo: Annotated[ScopedRepository, Depends(get_scoped_repo)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(None, description="Filter by status: SUCCESS, FAILED, PENDING"),
    order_id: str | None = Query(None, description="Filter by Order ID"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    txns: list[Transaction] = []
    try:
        # TODO(core): ScopedRepository.list_transactions (P2-C3)
        txns = await scoped_repo.list_transactions(status=status)
    except NotImplementedError:
        query = select(Transaction).where(Transaction.merchant_id == auth.active_merchant_id)
        if status:
            query = query.where(Transaction.status == status)
        if order_id:
            query = query.where(Transaction.order_id == order_id)
        query = query.limit(limit)
        txns = list((await session.execute(query)).scalars().all())

    items = [
        TransactionItemResponse(
            id=t.id,
            merchant_id=t.merchant_id,
            provider=t.provider,
            provider_txn_id=t.provider_txn_id,
            order_id=t.order_id,
            amount=t.amount,
            currency=t.currency,
            status=t.status,
            txn_time=t.txn_time,
            source_type=t.source_type,
        ).model_dump()
        for t in txns
    ]

    return success_response(
        data={"items": items, "total": len(items)}, source_type="SYNTHETIC_DEMO"
    )


@router.get("/transactions/{transaction_id}", summary="Tenant-scoped transaction detail")
async def get_transaction(
    transaction_id: uuid.UUID,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    # Query strictly scoped to merchant_id
    query = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.merchant_id == auth.active_merchant_id,
    )
    txn = (await session.execute(query)).scalar_one_or_none()

    if not txn:
        raise NotFoundError(f"Transaction {transaction_id} not found")

    # Check if settled
    entry_stmt = select(SettlementEntry).where(SettlementEntry.transaction_id == txn.id)
    entry = (await session.execute(entry_stmt)).scalar_one_or_none()

    return success_response(
        data=TransactionDetailResponse(
            id=txn.id,
            merchant_id=txn.merchant_id,
            provider=txn.provider,
            provider_txn_id=txn.provider_txn_id,
            order_id=txn.order_id,
            amount=txn.amount,
            currency=txn.currency,
            status=txn.status,
            txn_time=txn.txn_time,
            source_type=txn.source_type,
            settlement_status="SETTLED" if entry else "UNSETTLED",
            settlement_batch_ref="BATCH_20261112_01",
        ).model_dump(),
        source_type=txn.source_type,
    )
