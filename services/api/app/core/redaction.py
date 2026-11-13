from typing import Any


def redact_pii(text: str) -> str:
    """Redact PII (phone numbers, account numbers, card details, PAN, aadhaar) from text.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C3.
    """
    raise NotImplementedError("TODO(core): Codex task P2-C3")


def mask_phone(phone: str) -> str:
    """Mask phone number preserving last 4 digits (e.g., +91-XXXXX-XX89).

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C3.
    """
    raise NotImplementedError("TODO(core): Codex task P2-C3")


def mask_account(account: str) -> str:
    """Mask bank account number preserving last 4 digits.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C3.
    """
    raise NotImplementedError("TODO(core): Codex task P2-C3")


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys from dictionary payloads."""
    raise NotImplementedError("TODO(core): Codex task P2-C3")
