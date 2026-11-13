from fastapi import APIRouter

from app.core.config import settings
from app.core.response import success_response
from app.integrations import get_payment_provider

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    payment_prov = get_payment_provider()
    paytm_status = getattr(payment_prov, "integration_status", "UNAVAILABLE")

    return success_response(
        data={
            "status": "healthy",
            "environment": settings.APP_ENV,
            "demo_data_mode": settings.DEMO_DATA_MODE,
            "demo_deterministic": settings.DEMO_DETERMINISTIC,
            "llm_provider": settings.LLM_PROVIDER,
            "voice_provider": settings.VOICE_PROVIDER,
            "payment_provider": {
                "active": getattr(payment_prov, "last_source", "SYNTHETIC_DEMO"),
                "status": paytm_status,
                "environment": settings.PAYTM_ENVIRONMENT,
            },
            "settlement_ops_adapter": settings.SETTLEMENT_OPS_ADAPTER,
            "services": {"api": "up", "database": "configured", "verifier_role": "configured"},
        },
        source_type="SYSTEM",
    )
