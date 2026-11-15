import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import MerchantSummaryResponse
from app.core.dependencies import AuthContext, get_auth_context, get_scoped_repo
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.response import success_response
from app.db.models import Merchant, SettlementBatch, SupportCase, Transaction
from app.db.scoped_repository import ScopedRepository
from app.db.session import get_db_session

router = APIRouter()


@router.get("/merchants/{merchant_id}", summary="Tenant-scoped merchant summary")
async def get_merchant(
    merchant_id: uuid.UUID,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    scoped_repo: Annotated[ScopedRepository, Depends(get_scoped_repo)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    # Tenant Isolation: Merchant cannot access any other merchant's record
    if auth.role == "MERCHANT" and merchant_id != auth.active_merchant_id:
        raise ForbiddenError("Access to merchant data outside session scope is forbidden")

    merchant = None
    try:
        # TODO(core): ScopedRepository.get_merchant (P2-C3)
        target_repo = scoped_repo
        if auth.role in ("SUPERVISOR", "SUPPORT_AGENT") and merchant_id != auth.active_merchant_id:
            target_repo = ScopedRepository(session=session, merchant_id=merchant_id)
        merchant = await target_repo.get_merchant()
    except NotImplementedError:
        stmt = select(Merchant).where(Merchant.id == merchant_id)
        merchant = (await session.execute(stmt)).scalar_one_or_none()

    if not merchant or merchant.id != merchant_id:
        # If in demo mode and merchant_id matches, return demo profile
        if merchant_id == auth.active_merchant_id:
            txn_stmt = select(Transaction).where(
                Transaction.merchant_id == merchant_id,
                Transaction.status == "SUCCESS",
            )
            successful_txns = list((await session.execute(txn_stmt)).scalars().all())
            expected_net = sum((t.amount for t in successful_txns), Decimal("0.00"))

            batch_stmt = select(SettlementBatch).where(
                SettlementBatch.merchant_id == merchant_id
            )
            batches = list((await session.execute(batch_stmt)).scalars().all())
            observed_net = sum((b.net for b in batches), Decimal("0.00"))
            pending_amt = max(Decimal("0.00"), expected_net - observed_net)

            return success_response(
                data=MerchantSummaryResponse(
                    id=merchant_id,
                    external_mid="MID_DEMO_TWOBITS",
                    display_name="Paytm Smart Merchant Store",
                    masked_phone="+91-98765-43210",
                    status="ACTIVE",
                    created_at=datetime.now(UTC),
                    pending_settlement_amount=pending_amt,
                    open_cases_count=1,
                ).model_dump(),
                source_type="SYNTHETIC_DEMO",
            )
        raise NotFoundError(f"Merchant {merchant_id} not found")

    # Count open cases
    case_stmt = select(SupportCase).where(
        SupportCase.merchant_id == merchant.id,
        SupportCase.status.in_(
            [
                "NEW",
                "TRIAGED",
                "INVESTIGATING",
                "ACTION_REQUIRED",
                "AWAITING_APPROVAL",
                "IN_PROGRESS",
                "VERIFYING",
            ]
        ),
    )
    open_cases = len((await session.execute(case_stmt)).scalars().all())

    # Calculate pending settlement amount dynamically
    txn_stmt = select(Transaction).where(
        Transaction.merchant_id == merchant.id,
        Transaction.status == "SUCCESS",
    )
    successful_txns = list((await session.execute(txn_stmt)).scalars().all())
    expected_net = sum((t.amount for t in successful_txns), Decimal("0.00"))

    batch_stmt = select(SettlementBatch).where(
        SettlementBatch.merchant_id == merchant.id
    )
    batches = list((await session.execute(batch_stmt)).scalars().all())
    observed_net = sum((b.net for b in batches), Decimal("0.00"))
    pending_settlement = max(Decimal("0.00"), expected_net - observed_net)

    return success_response(
        data=MerchantSummaryResponse(
            id=merchant.id,
            external_mid=merchant.external_mid,
            display_name=merchant.display_name,
            masked_phone=merchant.masked_phone,
            status=merchant.status,
            created_at=merchant.created_at,
            pending_settlement_amount=pending_settlement,
            open_cases_count=open_cases,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
