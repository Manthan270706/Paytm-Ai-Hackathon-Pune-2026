import uuid
from decimal import Decimal

from fastapi import APIRouter

from app.api.v1.schemas import (
    DemoResetResponse,
    SimulateSettlementRequest,
    SimulateSettlementResponse,
)
from app.core.response import success_response

router = APIRouter()


@router.post(
    "/demo/simulate-settlement", summary="Simulate bank settlement credit (audited demo mode)"
)
async def simulate_settlement(req: SimulateSettlementRequest) -> dict:
    return success_response(
        data=SimulateSettlementResponse(
            message="Bank settlement simulation applied. ₹6,000 entry credited to synthetic batch.",
            added_entry_id=uuid.uuid4(),
            amount=req.amount,
            source_type="SYNTHETIC_DEMO",
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/demo/reset", summary="Reset demo state to frozen ₹15,000 / ₹9,000 / ₹6,000 scenario")
async def reset_demo_scenario() -> dict:
    return success_response(
        data=DemoResetResponse(
            message="Demo environment reset to frozen golden scenario successfully.",
            seeded_merchant_id=uuid.uuid4(),
            expected_net=Decimal("15000.00"),
            observed_net=Decimal("9000.00"),
            discrepancy=Decimal("6000.00"),
            status="OVERDUE",
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
