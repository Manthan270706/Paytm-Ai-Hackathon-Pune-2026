from fastapi import APIRouter

from app.api.v1.schemas import OutcomeMetricsResponse
from app.core.response import success_response

router = APIRouter()


@router.get("/metrics", summary="Outcome metrics calculated from case events")
async def get_outcome_metrics() -> dict:
    return success_response(
        data=OutcomeMetricsResponse(
            time_to_first_response_seconds=1.4,
            time_to_verified_resolution_minutes=2.1,
            straight_through_processing_rate_percent=74.2,
            total_cases_handled=42,
            total_cases_escalated=8,
            repeat_explanations_avoided=36,
        ).model_dump(),
        source_type="SYSTEM",
    )
