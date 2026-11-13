import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Header, HTTPException

from app.api.v1.schemas import (
    CaseApproveRequest,
    CaseAssignRequest,
    CaseCreateRequest,
    CaseDetailResponse,
    CaseEventResponse,
    CaseItemResponse,
    CaseRejectRequest,
    CaseVerifyResponse,
)
from app.core.response import success_response

router = APIRouter()


@router.get("/cases", summary="List support cases")
async def list_cases() -> dict:
    mock_case_id = uuid.uuid4()
    mock_merchant_id = uuid.uuid4()
    now = datetime.now(UTC)
    case_item = CaseItemResponse(
        id=mock_case_id,
        merchant_id=mock_merchant_id,
        case_number="CASE-2026-1024",
        category="SETTLEMENT_MISMATCH",
        priority="P1",
        status="AWAITING_APPROVAL",
        queue="SETTLEMENT_OPS",
        summary="Missing ₹6,000 from settlement batch BATCH_20261112_01",
        version=1,
        created_at=now,
        updated_at=now,
    )
    return success_response(
        data={"items": [case_item.model_dump()], "total": 1}, source_type="SYNTHETIC_DEMO"
    )


@router.post("/cases", summary="Create support case with Idempotency-Key")
async def create_case(
    req: CaseCreateRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    case_id = uuid.uuid4()
    now = datetime.now(UTC)
    return success_response(
        data=CaseItemResponse(
            id=case_id,
            merchant_id=uuid.uuid4(),
            case_number="CASE-2026-1024",
            category=req.category,
            priority=req.priority,
            status="NEW",
            queue="SETTLEMENT_OPS",
            summary=req.summary,
            version=1,
            created_at=now,
            updated_at=now,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/cases/{case_id}", summary="Case detail and timeline")
async def get_case(case_id: uuid.UUID) -> dict:
    now = datetime.now(UTC)
    return success_response(
        data=CaseDetailResponse(
            id=case_id,
            merchant_id=uuid.uuid4(),
            case_number="CASE-2026-1024",
            category="SETTLEMENT_MISMATCH",
            priority="P1",
            status="AWAITING_APPROVAL",
            queue="SETTLEMENT_OPS",
            summary="Missing ₹6,000 from settlement batch BATCH_20261112_01",
            version=1,
            created_at=now,
            updated_at=now,
            timeline=[
                CaseEventResponse(
                    id=uuid.uuid4(),
                    actor="OpsSaathi AI",
                    event_type="CASE_CREATED",
                    from_status=None,
                    to_status="NEW",
                    visibility="MERCHANT",
                    payload={"category": "SETTLEMENT_MISMATCH"},
                    created_at=now,
                ),
                CaseEventResponse(
                    id=uuid.uuid4(),
                    actor="OpsSaathi AI",
                    event_type="APPROVAL_REQUESTED",
                    from_status="NEW",
                    to_status="AWAITING_APPROVAL",
                    visibility="INTERNAL",
                    payload={"action": "SETTLEMENT_RESYNC", "amount": "6000.00"},
                    created_at=now,
                ),
            ],
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/approve", summary="Support role approval of gated action")
async def approve_case_action(case_id: uuid.UUID, req: CaseApproveRequest) -> dict:
    return success_response(
        data={
            "case_id": case_id,
            "status": "APPROVED",
            "new_version": req.expected_version + 1,
            "resync_status": "ACKNOWLEDGED",
            "message": "Settlement re-sync approved and scheduled.",
        },
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/reject", summary="Support role rejection of gated action")
async def reject_case_action(case_id: uuid.UUID, req: CaseRejectRequest) -> dict:
    return success_response(
        data={
            "case_id": case_id,
            "status": "REJECTED",
            "new_version": req.expected_version + 1,
            "reason": req.reason,
            "message": "Settlement re-sync rejected with documented reason.",
        },
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/assign", summary="Assign case to a support queue")
async def assign_case(case_id: uuid.UUID, req: CaseAssignRequest) -> dict:
    return success_response(
        data={
            "case_id": case_id,
            "queue": req.queue,
            "new_version": req.expected_version + 1,
            "message": f"Case assigned to {req.queue}.",
        },
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/verify", summary="Fresh independent verification via read-only role")
async def verify_case(case_id: uuid.UUID) -> dict:
    return success_response(
        data=CaseVerifyResponse(
            case_id=case_id,
            status="RESOLVED",
            verification_result="PASS",
            before_observed=Decimal("9000.00"),
            after_observed=Decimal("15000.00"),
            expected_net=Decimal("15000.00"),
            evidence_timestamp=datetime.now(UTC),
            verifier_role="opssaathi_verifier",
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/followup/run", summary="Manual follow-up worker trigger")
async def run_case_followup(case_id: uuid.UUID) -> dict:
    return success_response(
        data={
            "case_id": case_id,
            "job_status": "COMPLETED",
            "notification_sent": True,
            "message": "Follow-up check executed: status updated for merchant.",
        },
        source_type="SYNTHETIC_DEMO",
    )
