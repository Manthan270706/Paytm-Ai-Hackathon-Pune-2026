import inspect

import pytest

from app.core.webhook import deduplicate_webhook, verify_paytm_signature


def test_webhook_signatures_and_stubs() -> None:
    assert list(inspect.signature(verify_paytm_signature).parameters.keys()) == [
        "payload_bytes",
        "signature",
        "merchant_key",
    ]
    assert list(inspect.signature(deduplicate_webhook).parameters.keys()) == [
        "event_id",
        "session",
    ]

    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P4-C1"):
        verify_paytm_signature(b"{}", "sig", "key")


@pytest.mark.asyncio
async def test_deduplicate_webhook_stub() -> None:
    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P4-C1"):
        await deduplicate_webhook("evt_123", None)  # type: ignore[arg-type]
