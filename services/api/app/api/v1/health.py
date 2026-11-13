from fastapi import APIRouter

from app.core.config import settings
from app.core.response import success_response

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return success_response(
        data={
            "status": "healthy",
            "environment": settings.APP_ENV,
            "demo_data_mode": settings.DEMO_DATA_MODE,
            "demo_deterministic": settings.DEMO_DETERMINISTIC,
            "llm_provider": settings.LLM_PROVIDER,
            "voice_provider": settings.VOICE_PROVIDER,
            "settlement_ops_adapter": settings.SETTLEMENT_OPS_ADAPTER,
            "services": {
                "api": "up",
                "database": "configured",
                "verifier_role": "configured"
            }
        },
        source_type="SYSTEM"
    )
