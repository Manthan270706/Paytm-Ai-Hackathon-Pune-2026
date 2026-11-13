import json
import logging
import uuid
from typing import Annotated, Any
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.response import success_response
from app.core.webhook import deduplicate_webhook
from app.core.webhook import verify_paytm_signature as validate_paytm_checksum
from app.db.models import AuditEvent
from app.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/webhooks/paytm", summary="Public Paytm payment callback / webhook with deduplication"
)
async def receive_paytm_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_paytm_signature: Annotated[str | None, Header(alias="x-paytm-signature")] = None,
) -> dict[str, Any]:
    raw_bytes = await request.body()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty webhook payload")

    # Parse payload (JSON or Form URL-encoded)
    params: dict[str, Any] = {}
    content_type = request.headers.get("content-type", "")
    try:
        raw_text = raw_bytes.decode("utf-8")
        if "application/json" in content_type or raw_text.lstrip().startswith("{"):
            params = json.loads(raw_text)
        else:
            params = dict(parse_qsl(raw_text, keep_blank_values=True))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}") from exc

    # Extract event ID
    event_id = str(
        params.get("event_id")
        or params.get("ORDERID")
        or params.get("order_id")
        or request.headers.get("x-paytm-event-id")
        or uuid.uuid4()
    )

    # Extract signature (Header, CHECKSUMHASH, or checksum field)
    signature = str(x_paytm_signature or params.get("CHECKSUMHASH") or params.get("checksum") or "")

    # 1. Signature Verification per PRD §13 and P4-C1 (always execute cryptographic validation)
    merchant_key = settings.PAYTM_MERCHANT_KEY or ""
    is_valid = validate_paytm_checksum(raw_bytes, signature, merchant_key)

    is_demo_bypass = False
    # Demo mode fallback for seeded integration tests ONLY when DEMO_DATA_MODE is explicitly True
    if not is_valid and settings.DEMO_DATA_MODE:
        if validate_paytm_checksum(raw_bytes, signature, "0123456789abcdef"):
            is_valid = True
            is_demo_bypass = True

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Paytm webhook signature verification failed",
        )

    # When demo bypass occurs, stored records/responses must be SYNTHETIC_DEMO, not PAYTM_STAGING
    source_type = "SYNTHETIC_DEMO" if is_demo_bypass else "PAYTM_STAGING"

    # 2. Idempotent Deduplication per PRD §13 and P4-C1
    is_new = await deduplicate_webhook(event_id, session, payload_bytes=raw_bytes)

    audit_id = uuid.uuid4()
    audit_row = AuditEvent(
        id=audit_id,
        actor="PAYTM_WEBHOOK",
        action="WEBHOOK_PROCESSED" if is_new else "WEBHOOK_DUPLICATE_IGNORED",
        resource=f"webhook_events/{event_id}",
        trace_id=str(audit_id),
        payload={
            "event_id": event_id,
            "status": "PROCESSED" if is_new else "DUPLICATE_IGNORED",
            "source_type": source_type,
            "demo_bypass": is_demo_bypass,
        },
    )
    session.add(audit_row)
    await session.commit()

    if not is_new:
        return success_response(
            data={
                "received": True,
                "event_id": event_id,
                "deduplicated": False,
                "signature_valid": True,
                "status": "DUPLICATE_IGNORED",
                "message": "Webhook event previously processed",
            },
            source_type=source_type,
        )

    return success_response(
        data={
            "received": True,
            "event_id": event_id,
            "deduplicated": True,
            "signature_valid": True,
            "status": "PROCESSED",
            "audit_id": str(audit_id),
        },
        source_type=source_type,
    )
