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
from app.db.models import Merchant, SupportCase
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

    # Call ScopedRepository stub with fallback
    merchant = None
    try:
        # TODO(core): ScopedRepository.get_merchant (P2-C3)
        merchant = await scoped_repo.get_merchant()
    except NotImplementedError:
        stmt = select(Merchant).where(Merchant.id == merchant_id)
        merchant = (await session.execute(stmt)).scalar_one_or_none()

    if not merchant:
        # If in demo mode and merchant_id matches, return demo profile
        if merchant_id == auth.active_merchant_id:
            return success_response(
                data=MerchantSummaryResponse(
                    id=merchant_id,
                    external_mid="MID_DEMO_TWOBITS",
                    display_name="Two Bits Chai & Snacks",
                    masked_phone="+91-98765-43210",
                    status="ACTIVE",
                    created_at=datetime.now(UTC),
                    pending_settlement_amount=Decimal("6000.00"),
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

    return success_response(
        data=MerchantSummaryResponse(
            id=merchant.id,
            external_mid=merchant.external_mid,
            display_name=merchant.display_name,
            masked_phone=merchant.masked_phone,
            status=merchant.status,
            created_at=merchant.created_at,
            pending_settlement_amount=Decimal("6000.00"),
            open_cases_count=open_cases,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
