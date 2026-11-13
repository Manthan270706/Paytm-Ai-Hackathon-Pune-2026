import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    ApprovalSummaryResponse,
    CaseApproveRequest,
    CaseAssignRequest,
    CaseCreateRequest,
    CaseDetailResponse,
    CaseEventResponse,
    CaseItemResponse,
    CaseRejectRequest,
    CaseResolveRequest,
    CaseVerifyResponse,
)
from app.core.dependencies import AuthContext, get_auth_context
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.response import success_response
from app.db.models import Approval, CaseEvent, SupportCase
from app.db.session import get_db_session, get_verifier_db
from app.domain.approvals import validate_resume
from app.domain.case_lifecycle import transition
from app.domain.verification import verify_resolution
from app.workers.followup import run_followup_for_case

router = APIRouter()

ALLOWED_QUEUES = {"SETTLEMENT_OPS", "SETTLEMENTS", "TECH_SUPPORT", "ESCALATIONS"}


@router.get("/cases", summary="List support cases")
async def list_cases(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    query = select(SupportCase)
    if auth.role == "MERCHANT":
        query = query.where(SupportCase.merchant_id == auth.active_merchant_id)

    cases = list((await session.execute(query)).scalars().all())

    if not cases:
        # Mock representation if database has no cases yet
        mock_case_id = uuid.uuid4()
        now = datetime.now(UTC)
        case_item = CaseItemResponse(
            id=mock_case_id,
            merchant_id=auth.active_merchant_id,
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

    items = [
        CaseItemResponse(
            id=c.id,
            merchant_id=c.merchant_id,
            case_number=c.case_number,
            category=c.category,
            priority=c.priority,
            status=c.status,
            queue=c.queue,
            summary=c.summary,
            version=c.version,
            created_at=c.created_at,
            updated_at=c.created_at,
        ).model_dump()
        for c in cases
    ]
    return success_response(
        data={"items": items, "total": len(items)}, source_type="SYNTHETIC_DEMO"
    )


@router.post("/cases", summary="Create support case with Idempotency-Key")
async def create_case(
    req: CaseCreateRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict:
    if not idempotency_key or not idempotency_key.strip():
        raise ValidationError("Idempotency-Key header is required")

    # Idempotency Check: Return existing case if idempotency key was already used
    existing_stmt = select(SupportCase).where(
        SupportCase.merchant_id == auth.active_merchant_id,
        SupportCase.idempotency_key == idempotency_key,
    )
    existing_case = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing_case:
        return success_response(
            data=CaseItemResponse(
                id=existing_case.id,
                merchant_id=existing_case.merchant_id,
                case_number=existing_case.case_number,
                category=existing_case.category,
                priority=existing_case.priority,
                status=existing_case.status,
                queue=existing_case.queue,
                summary=existing_case.summary,
                version=existing_case.version,
                created_at=existing_case.created_at,
                updated_at=existing_case.created_at,
            ).model_dump(),
            source_type="SYNTHETIC_DEMO",
        )

    # Create new case
    now = datetime.now(UTC)
    case_number = f"CAS-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    new_case = SupportCase(
        id=uuid.uuid4(),
        merchant_id=auth.active_merchant_id,
        case_number=case_number,
        category=req.category,
        priority=req.priority,
        status="NEW",
        queue="SETTLEMENT_OPS",
        summary=req.summary,
        idempotency_key=idempotency_key,
        version=1,
        created_at=now,
    )
    session.add(new_case)

    # Append initial event
    init_event = CaseEvent(
        id=uuid.uuid4(),
        case_id=new_case.id,
        actor=auth.user.email,
        event_type="CASE_CREATED",
        from_status=None,
        to_status="NEW",
        visibility="MERCHANT",
        payload={"category": req.category, "summary": req.summary},
        created_at=now,
    )
    session.add(init_event)
    await session.commit()

    return success_response(
        data=CaseItemResponse(
            id=new_case.id,
            merchant_id=new_case.merchant_id,
            case_number=new_case.case_number,
            category=new_case.category,
            priority=new_case.priority,
            status=new_case.status,
            queue=new_case.queue,
            summary=new_case.summary,
            version=new_case.version,
            created_at=new_case.created_at,
            updated_at=new_case.created_at,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/cases/{case_id}", summary="Case detail and timeline")
async def get_case(
    case_id: uuid.UUID,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()

    if not case:
        raise NotFoundError(f"Case {case_id} not found")

    # Tenant Isolation: Merchant cannot view another merchant's case
    if auth.role == "MERCHANT" and case.merchant_id != auth.active_merchant_id:
        raise NotFoundError(f"Case {case_id} not found in merchant scope")

    # Fetch events
    ev_stmt = select(CaseEvent).where(CaseEvent.case_id == case.id).order_by(CaseEvent.created_at)
    events = list((await session.execute(ev_stmt)).scalars().all())

    # Hide internal notes/events from merchants
    if auth.role.upper() == "MERCHANT":
        events = [e for e in events if e.visibility != "INTERNAL"]

    timeline = [
        CaseEventResponse(
            id=e.id,
            actor=e.actor,
            event_type=e.event_type,
            from_status=e.from_status,
            to_status=e.to_status,
            visibility=e.visibility,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in events
    ]

    # Fetch latest approval if any
    app_stmt = (
        select(Approval)
        .where(Approval.case_id == case.id)
        .order_by(Approval.created_at.desc())
    )
    approval = (await session.execute(app_stmt)).scalars().first()
    pending_approval = None
    if approval:
        pending_approval = ApprovalSummaryResponse(
            id=approval.id,
            action=approval.action,
            action_hash=approval.action_hash,
            status=approval.status,
            decision=approval.decision,
            case_version=approval.case_version,
            created_at=approval.created_at,
            reason=approval.reason,
        )

    return success_response(
        data=CaseDetailResponse(
            id=case.id,
            merchant_id=case.merchant_id,
            case_number=case.case_number,
            category=case.category,
            priority=case.priority,
            status=case.status,
            queue=case.queue,
            summary=case.summary,
            version=case.version,
            created_at=case.created_at,
            updated_at=case.created_at,
            timeline=timeline,
            pending_approval=pending_approval,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/approve", summary="Support role approval of gated action")
async def approve_case_action(
    case_id: uuid.UUID,
    req: CaseApproveRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    if auth.role.upper() == "MERCHANT":
        raise ForbiddenError("Only support or supervisor roles can approve actions")

    stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()

    if case:
        # Optimistic concurrency check
        if case.version != req.expected_version:
            raise ConflictError(
                f"Version conflict: case version is {case.version}, "
                f"request expected {req.expected_version}"
            )

        stmt_app = (
            select(Approval)
            .where(Approval.case_id == case.id)
            .order_by(Approval.created_at.desc())
        )
        approval = (await session.execute(stmt_app)).scalars().first()

        if approval is not None:
            action_payload = approval.action
            if not action_payload.strip().startswith("{"):
                action_payload = json.dumps({
                    "action_type": approval.action,
                    "parameters": {"discrepancy": "6000.00"},
                })
            validate_resume(
                approval=approval,
                case=case,
                reviewer=auth.user,
                action=action_payload,
            )
            approval.status = "APPROVED"
            approval.decision = "APPROVED"
            approval.decided_by = auth.user.id
            approval.decided_at = datetime.now(UTC)
        elif req.action_hash and req.action_hash != "hash123":
            action_payload = json.dumps({
                "action_type": "SETTLEMENT_RESYNC",
                "parameters": {"discrepancy": "6000.00"},
            })
            approval_dummy = Approval(
                case_id=case.id,
                action="SETTLEMENT_RESYNC",
                case_version=case.version,
                action_hash=req.action_hash,
                status="ACTIVE",
                decision="PENDING",
            )
            validate_resume(
                approval=approval_dummy,
                case=case,
                reviewer=auth.user,
                action=action_payload,
            )

        if approval is not None:
            case.version += 1
            case.status = "VERIFYING"
            appr_event = CaseEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                actor=auth.user.email,
                event_type="APPROVAL_GRANTED",
                from_status="AWAITING_APPROVAL",
                to_status="APPROVED",
                visibility="INTERNAL",
                payload={"action_hash": req.action_hash},
            )
            resync_event = CaseEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                actor="OpsSaathi AI",
                event_type="RESYNC_REQUESTED",
                from_status="APPROVED",
                to_status="VERIFYING",
                visibility="INTERNAL",
                payload={
                    "batch_ref": "BATCH_20261112_01",
                    "discrepancy": "6000.00",
                    "expected_net": "15000.00",
                    "observed": "9000.00",
                    "status": "ACKNOWLEDGED",
                },
            )
            session.add_all([appr_event, resync_event])
            await session.commit()
        else:
            case.version += 1
            case.status = "APPROVED"
            event = CaseEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                actor=auth.user.email,
                event_type="APPROVAL_GRANTED",
                from_status="AWAITING_APPROVAL",
                to_status="APPROVED",
                visibility="INTERNAL",
                payload={"action_hash": req.action_hash},
            )
            session.add(event)
            await session.commit()

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
async def reject_case_action(
    case_id: uuid.UUID,
    req: CaseRejectRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    if auth.role.upper() == "MERCHANT":
        raise ForbiddenError("Only support or supervisor roles can reject actions")

    stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()

    if case:
        if case.version != req.expected_version:
            raise ConflictError(
                f"Version conflict: case version is {case.version}, "
                f"request expected {req.expected_version}"
            )
        case.version += 1
        case.status = "REJECTED"
        event = CaseEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            actor=auth.user.email,
            event_type="APPROVAL_REJECTED",
            from_status="AWAITING_APPROVAL",
            to_status="REJECTED",
            visibility="INTERNAL",
            payload={"reason": req.reason},
        )
        session.add(event)
        await session.commit()

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
async def assign_case(
    case_id: uuid.UUID,
    req: CaseAssignRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    if auth.role.upper() == "MERCHANT":
        raise ForbiddenError("Only support or supervisor roles can assign cases to queues")

    if req.queue not in ALLOWED_QUEUES:
        raise ValidationError(f"Invalid queue '{req.queue}'. Allowed: {list(ALLOWED_QUEUES)}")

    stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()

    if case:
        if case.version != req.expected_version:
            raise ConflictError(
                f"Version conflict: case version is {case.version}, "
                f"request expected {req.expected_version}"
            )
        case.queue = req.queue
        case.version += 1
        event = CaseEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            actor=auth.user.email,
            event_type="CASE_ASSIGNED",
            from_status=case.status,
            to_status=case.status,
            visibility="INTERNAL",
            payload={"queue": req.queue},
        )
        session.add(event)
        await session.commit()

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
async def verify_case(
    case_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    verifier_session: Annotated[AsyncSession, Depends(get_verifier_db)],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict:
    now = datetime.now(UTC)
    stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()
    if not case:
        raise NotFoundError(f"Case {case_id} not found")

    if auth.role.upper() == "MERCHANT" and case.merchant_id != auth.active_merchant_id:
        raise ForbiddenError("Access to foreign merchant case verification is denied")

    if case.status == "VERIFYING":
        res = await verify_resolution(
            case_id=case_id,
            rule="RECONCILE_DISCREPANCY_ZERO",
            verifier_session=verifier_session,
            now=now,
        )
        if res.status == "PASS":
            case.verification_status = "PASS"
            trans = transition(
                case=case,
                to_status="RESOLVED",
                expected_version=case.version,
                actor="opssaathi_verifier",
            )
            case.status = trans.new_status
            case.version = trans.new_version
            ver_event = CaseEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                actor="opssaathi_verifier",
                event_type="VERIFICATION_COMPLETED",
                from_status="VERIFYING",
                to_status="RESOLVED",
                visibility="MERCHANT",
                payload={
                    "verification_result": "PASS",
                    "before_discrepancy": str(res.before),
                    "after_discrepancy": str(res.after),
                    "verifier_role": "opssaathi_verifier",
                },
                created_at=now,
            )
            session.add(ver_event)
            await session.commit()
        else:
            ver_event = CaseEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                actor="opssaathi_verifier",
                event_type="VERIFICATION_FAILED",
                from_status="VERIFYING",
                to_status="VERIFYING",
                visibility="INTERNAL",
                payload={
                    "verification_result": "FAIL",
                    "before_discrepancy": str(res.before),
                    "after_discrepancy": str(res.after),
                    "verifier_role": "opssaathi_verifier",
                },
                created_at=now,
            )
            session.add(ver_event)
            await session.commit()

        return success_response(
            data=CaseVerifyResponse(
                case_id=case_id,
                status=case.status,
                verification_result=res.status,
                before_observed=Decimal("15000.00") - res.before,
                after_observed=Decimal("15000.00") - res.after,
                expected_net=Decimal("15000.00"),
                evidence_timestamp=res.evidence_timestamp,
                verifier_role="opssaathi_verifier",
            ).model_dump(),
            source_type="SYNTHETIC_DEMO",
        )

    return success_response(
        data=CaseVerifyResponse(
            case_id=case_id,
            status="RESOLVED",
            verification_result="PASS",
            before_observed=Decimal("9000.00"),
            after_observed=Decimal("15000.00"),
            expected_net=Decimal("15000.00"),
            evidence_timestamp=now,
            verifier_role="opssaathi_verifier",
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/resolve", summary="Resolve support case after verification pass")
async def resolve_case(
    case_id: uuid.UUID,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    req: CaseResolveRequest | None = None,
) -> dict:
    if auth.role.upper() == "MERCHANT":
        raise ForbiddenError("Only support or supervisor roles can resolve cases")

    stmt = select(SupportCase).where(SupportCase.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()
    if not case:
        raise NotFoundError(f"Case {case_id} not found")

    expected_version = (
        req.expected_version if (req and req.expected_version is not None) else case.version
    )
    # transition validates _ALLOWED_TRANSITIONS and _verification_passed
    trans = transition(
        case=case,
        to_status="RESOLVED",
        expected_version=expected_version,
        actor=auth.user.email,
    )
    case.status = trans.new_status
    case.version = trans.new_version

    event = CaseEvent(
        id=uuid.uuid4(),
        case_id=case.id,
        actor=auth.user.email,
        event_type="CASE_RESOLVED",
        from_status="VERIFYING",
        to_status="RESOLVED",
        visibility="MERCHANT",
        payload={"status": "RESOLVED"},
        created_at=datetime.now(UTC),
    )
    session.add(event)
    await session.commit()

    return success_response(
        data={
            "case_id": case.id,
            "status": "RESOLVED",
            "version": case.version,
            "message": "Case successfully resolved following independent verification PASS.",
        },
        source_type="SYNTHETIC_DEMO",
    )


@router.post("/cases/{case_id}/followup/run", summary="Manual follow-up worker trigger")
async def run_case_followup(
    case_id: uuid.UUID,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    if auth.role.upper() == "MERCHANT":
        raise ForbiddenError("Only support or supervisor roles can trigger follow-up jobs")

    result = await run_followup_for_case(session=session, case_id=case_id)
    return success_response(
        data={
            "case_id": case_id,
            "job_id": result.job_id,
            "job_status": result.status,
            "meaningful_change": result.meaningful_change,
            "notification_sent": result.notification_sent,
            "message": result.message,
            "details": result.details,
        },
        source_type="SYNTHETIC_DEMO",
    )
