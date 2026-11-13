from sqlalchemy.ext.asyncio import AsyncSession


def verify_paytm_signature(
    payload_bytes: bytes,
    signature: str,
    merchant_key: str,
) -> bool:
    """Verify Paytm webhook HMAC signature against raw request bytes.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P4-C1.
    """
    raise NotImplementedError("TODO(core): Codex task P4-C1")


async def deduplicate_webhook(
    event_id: str,
    session: AsyncSession,
) -> bool:
    """Check webhook event ID uniqueness in webhook_events table.

    Returns True if event is new and recorded; False if duplicate replay.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P4-C1.
    """
    raise NotImplementedError("TODO(core): Codex task P4-C1")
