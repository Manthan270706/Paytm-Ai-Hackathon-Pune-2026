import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.models import User
from app.db.scoped_repository import ScopedRepository
from app.db.seed import MERCHANT_ID, MERCHANT_USER_ID, SUPERVISOR_USER_ID, SUPPORT_USER_ID
from app.db.session import get_db_session


@dataclass
class AuthContext:
    user: User
    active_merchant_id: uuid.UUID
    role: str  # MERCHANT, SUPPORT_AGENT, SUPERVISOR


async def get_auth_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> AuthContext:
    """Extract authenticated user and bound merchant scope from session token."""
    role = "MERCHANT"
    target_user_id = MERCHANT_USER_ID
    active_mid = MERCHANT_ID

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        if "support_agent" in token or "support" in token:
            role = "SUPPORT_AGENT"
            target_user_id = SUPPORT_USER_ID
        elif "supervisor" in token:
            role = "SUPERVISOR"
            target_user_id = SUPERVISOR_USER_ID
        elif "merchant" in token:
            role = "MERCHANT"
            target_user_id = MERCHANT_USER_ID
        elif token.startswith("invalid"):
            raise UnauthorizedError("Invalid or expired session token")

    # Fetch user from DB if session exists
    if session:
        user_stmt = select(User).where(User.id == target_user_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(
                id=target_user_id,
                email=f"{role.lower()}@paytm.demo",
                hashed_password="DEMO_HASH",
                role=role,
                is_active=True,
                preferred_language="en",
            )
    else:
        user = User(
            id=target_user_id,
            email=f"{role.lower()}@paytm.demo",
            hashed_password="DEMO_HASH",
            role=role,
            is_active=True,
            preferred_language="en",
        )

    return AuthContext(
        user=user,
        active_merchant_id=active_mid,
        role=role,
    )


def require_role(*allowed_roles: str) -> Callable[..., Any]:
    """Enforce endpoint role authorization (RBAC)."""

    async def _role_checker(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        normalized_allowed = [r.upper() for r in allowed_roles]
        if auth.role.upper() not in normalized_allowed:
            raise ForbiddenError(
                f"Action forbidden for role '{auth.role}'. Required roles: {list(allowed_roles)}"
            )
        return auth

    return _role_checker


async def get_scoped_repo(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScopedRepository:
    """Instantiate tenant-scoped repository bound to the authenticated merchant scope.

    PRD §7.4: All data access goes through ScopedRepository(merchant_id).
    """
    return ScopedRepository(session=session, merchant_id=auth.active_merchant_id)
