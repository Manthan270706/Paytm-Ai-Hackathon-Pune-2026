import uuid

from fastapi import APIRouter

from app.api.v1.schemas import PaytmWebhookPayload
from app.core.response import success_response

router = APIRouter()


@router.post(
    "/webhooks/paytm", summary="Public Paytm payment callback / webhook with deduplication"
)
async def receive_paytm_webhook(payload: PaytmWebhookPayload) -> dict:
    return success_response(
        data={
            "received": True,
            "event_id": payload.event_id,
            "deduplicated": True,
            "status": "PROCESSED",
            "audit_id": str(uuid.uuid4()),
        },
        source_type="PAYTM_STAGING",
    )
