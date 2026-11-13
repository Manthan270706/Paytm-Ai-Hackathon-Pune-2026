"""Demo session role parsing and default-deny role authorization helpers."""

import re
from dataclasses import dataclass
from typing import Final

VALID_ROLES: Final[frozenset[str]] = frozenset({"MERCHANT", "SUPPORT_AGENT", "SUPERVISOR"})
_DEMO_TOKEN = re.compile(
    r"demo-token-(merchant|support_agent|supervisor)-([a-z0-9-]+)", re.IGNORECASE
)


@dataclass(frozen=True)
class DemoIdentity:
    role: str
    subject: str


def parse_demo_token(token: str) -> DemoIdentity | None:
    """Parse only the complete demo-token format; never infer roles by substring."""
    match = _DEMO_TOKEN.fullmatch(token.strip())
    if match is None:
        return None
    role, subject = match.groups()
    normalized_role = role.upper()
    if normalized_role not in VALID_ROLES:
        return None
    return DemoIdentity(role=normalized_role, subject=subject)


def is_role_allowed(role: str, allowed_roles: tuple[str, ...]) -> bool:
    """Return false for empty, unknown, or mismatched role allowlists."""
    normalized_role = role.upper() if isinstance(role, str) else ""
    normalized_allowed = {item.upper() for item in allowed_roles if isinstance(item, str)}
    if normalized_role not in VALID_ROLES or not normalized_allowed:
        return False
    if not normalized_allowed <= VALID_ROLES:
        return False
    return normalized_role in normalized_allowed
