from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    DemoResetResponse,
    SimulateSettlementRequest,
    SimulateSettlementResponse,
)
from app.core.response import success_response
from app.db.seed import reset_and_seed, simulate_bank_settlement
from app.db.session import get_db_session

router = APIRouter()


@router.post(
    "/demo/simulate-settlement", summary="Simulate bank settlement credit (audited demo mode)"
)
async def simulate_settlement(
    req: SimulateSettlementRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    result = await simulate_bank_settlement(session)
    return success_response(
        data=SimulateSettlementResponse(
            message="Bank settlement simulation applied. ₹6,000 entry credited to synthetic batch.",
            added_entry_id=result["entry_id"],
            amount=result["amount"],
            source_type=result["source_type"],
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/demo/reset", summary="Reset demo state to frozen ₹15,000 / ₹9,000 / ₹6,000 scenario")
async def reset_demo_scenario(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    seed_result = await reset_and_seed(session)
    return success_response(
        data=DemoResetResponse(
            message="Demo environment reset to frozen golden scenario successfully.",
            seeded_merchant_id=seed_result["merchant_id"],
            expected_net=seed_result["expected_net"],
            observed_net=seed_result["observed_net"],
            discrepancy=seed_result["discrepancy"],
            status=seed_result["reason_code"],
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
