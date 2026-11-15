from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.response import success_response
from app.db.session import get_db_session
from app.integrations import get_payment_provider

router = APIRouter()


@router.get("/health")
async def health_check(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Safe liveness and integration readiness check. Never exposes credentials."""
    payment_prov = get_payment_provider()
    paytm_status = getattr(payment_prov, "integration_status", "UNAVAILABLE")

    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    return success_response(
        data={
            "status": "healthy",
            "environment": settings.APP_ENV,
            "demo_data_mode": settings.DEMO_DATA_MODE,
            "demo_deterministic": settings.DEMO_DETERMINISTIC,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_cascade": getattr(settings, "LLM_CASCADE", "groq,ollama,cache,mock"),
            "llm_active_tier": getattr(get_llm_provider(), "last_served_from", "UNKNOWN"),
            "voice_provider": settings.VOICE_PROVIDER,
            "payment_provider": {
                "active": getattr(payment_prov, "last_source", "SYNTHETIC_DEMO"),
                "status": paytm_status,
                "environment": settings.PAYTM_ENVIRONMENT,
            },
            "settlement_ops_adapter": settings.SETTLEMENT_OPS_ADAPTER,
            "services": {
                "api": "up",
                "database": db_status,
                "verifier_role": "configured",
            },
        },
        source_type="SYSTEM",
    )
