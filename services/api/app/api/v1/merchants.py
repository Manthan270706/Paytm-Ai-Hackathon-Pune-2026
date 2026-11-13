import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter

from app.api.v1.schemas import MerchantSummaryResponse
from app.core.response import success_response

router = APIRouter()


@router.get("/merchants/{merchant_id}", summary="Tenant-scoped merchant summary")
async def get_merchant(merchant_id: uuid.UUID) -> dict:
    return success_response(
        data=MerchantSummaryResponse(
            id=merchant_id,
            external_mid="MID_TEST_102938",
            display_name="Ramesh Kirana Store",
            masked_phone="+91 98*** **321",
            status="ACTIVE",
            created_at=datetime.now(UTC),
            pending_settlement_amount=Decimal("6000.00"),
            open_cases_count=1,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
