import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import is_role_allowed, parse_demo_token
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

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id


async def get_auth_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> AuthContext:
    """Extract authenticated user and bound merchant scope from session token."""
    if authorization is None:
        raise UnauthorizedError("A valid bearer session token is required")

    role = "MERCHANT"
    target_user_id = MERCHANT_USER_ID
    active_mid = MERCHANT_ID

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise UnauthorizedError("A valid bearer session token is required")
    identity = parse_demo_token(token)
    if identity is None:
        raise UnauthorizedError("Invalid or expired session token")
    role = identity.role
    if role == "SUPPORT_AGENT":
        target_user_id = SUPPORT_USER_ID
    elif role == "SUPERVISOR":
        target_user_id = SUPERVISOR_USER_ID
    elif role == "MERCHANT":
        if identity.subject == "2":
            active_mid = uuid.UUID("22222222-2222-2222-2222-222222222222")
            target_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "merchant2@paytm.demo")
        else:
            target_user_id = MERCHANT_USER_ID

    # Fetch user from DB if session exists
    if session:
        user_stmt = select(User).where(User.id == target_user_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if user and (not user.is_active or user.role.upper() != role):
            raise UnauthorizedError("Session user is inactive or has a different role")
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
        if not is_role_allowed(auth.role, allowed_roles):
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
