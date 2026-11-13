import uuid

from fastapi import APIRouter

from app.api.v1.schemas import CurrentUserResponse, DemoLoginRequest, DemoLoginResponse
from app.core.response import success_response

router = APIRouter()


@router.post("/auth/demo-login", summary="Start demo session")
async def demo_login(req: DemoLoginRequest) -> dict:
    mock_merchant_id = uuid.uuid4()
    mock_user_id = uuid.uuid4()
    return success_response(
        data=DemoLoginResponse(
            access_token=f"demo-token-{req.role.lower()}-{mock_user_id}",
            token_type="bearer",
            role=req.role.upper(),
            user_id=mock_user_id,
            merchant_id=mock_merchant_id if req.role.upper() == "MERCHANT" else None,
            display_name="Ramesh Kirana Store"
            if req.role.upper() == "MERCHANT"
            else "Support Lead",
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/me", summary="Current user and allowed merchant scope")
async def get_current_user() -> dict:
    mock_user_id = uuid.uuid4()
    mock_merchant_id = uuid.uuid4()
    return success_response(
        data=CurrentUserResponse(
            user_id=mock_user_id,
            email="merchant@paytm.demo",
            role="MERCHANT",
            is_active=True,
            preferred_language="en",
            allowed_merchant_ids=[mock_merchant_id],
            active_merchant_id=mock_merchant_id,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
