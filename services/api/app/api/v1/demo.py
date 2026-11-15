import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    DemoResetResponse,
    SimulateSettlementRequest,
    SimulateSettlementResponse,
)
from app.core.config import settings
from app.core.dependencies import AuthContext, get_auth_context
from app.core.exceptions import ForbiddenError
from app.core.response import success_response
from app.db.models import AuditEvent
from app.db.seed import reset_and_seed, simulate_bank_settlement
from app.db.session import get_db_session

router = APIRouter()


@router.post(
    "/demo/simulate-settlement", summary="Simulate bank settlement credit (audited demo mode)"
)
async def simulate_settlement(
    req: SimulateSettlementRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict:
    if not settings.DEMO_DATA_MODE:
        raise ForbiddenError("Demo actions require DEMO_DATA_MODE=true")
    if auth.role.upper() not in {"SUPPORT_AGENT", "SUPERVISOR"}:
        raise ForbiddenError("Demo actions require support or supervisor role")

    result = await simulate_bank_settlement(session)

    audit_id = uuid.uuid4()
    audit_event = AuditEvent(
        id=audit_id,
        actor=auth.user.email,
        action="DEMO_SIMULATE_SETTLEMENT",
        resource=f"settlement_batches/{req.batch_ref}",
        trace_id=str(audit_id),
        payload={
            "amount": str(result["amount"]),
            "entry_id": str(result["entry_id"]),
            "source_type": result["source_type"],
            "requested_amount": str(req.amount) if req.amount else None,
            "batch_ref": req.batch_ref,
        },
    )
    session.add(audit_event)
    await session.commit()

    return success_response(
        data=SimulateSettlementResponse(
            message=f"Bank settlement simulation applied. ₹{result['amount']} entry credited to batch {req.batch_ref}.",
            added_entry_id=result["entry_id"],
            amount=result["amount"],
            source_type=result["source_type"],
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/demo/reset", summary="Reset demo state to frozen ₹15,000 / ₹9,000 / ₹6,000 scenario")
async def reset_demo_scenario(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict:
    if not settings.DEMO_DATA_MODE:
        raise ForbiddenError("Demo actions require DEMO_DATA_MODE=true")
    if auth.role.upper() not in {"SUPPORT_AGENT", "SUPERVISOR"}:
        raise ForbiddenError("Demo actions require support or supervisor role")

    seed_result = await reset_and_seed(session)

    audit_id = uuid.uuid4()
    audit_event = AuditEvent(
        id=audit_id,
        actor=auth.user.email,
        action="DEMO_RESET",
        resource="demo/frozen_scenario",
        trace_id=str(audit_id),
        payload={
            "merchant_id": str(seed_result["merchant_id"]),
            "expected_net": str(seed_result["expected_net"]),
            "observed_net": str(seed_result["observed_net"]),
            "discrepancy": str(seed_result["discrepancy"]),
        },
    )
    session.add(audit_event)
    await session.commit()

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
