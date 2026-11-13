import inspect
import uuid

import pytest

from app.core.redaction import mask_account, mask_phone, redact_pii
from app.db.scoped_repository import ScopedRepository


@pytest.mark.asyncio
async def test_scoped_repository_stubs() -> None:
    repo = ScopedRepository(session=None, merchant_id=uuid.uuid4())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P2-C3"):
        await repo.get_merchant()


def test_redaction_stubs() -> None:
    assert list(inspect.signature(redact_pii).parameters.keys()) == ["text"]
    assert list(inspect.signature(mask_phone).parameters.keys()) == ["phone"]
    assert list(inspect.signature(mask_account).parameters.keys()) == ["account"]

    with pytest.raises(NotImplementedError, match="TODO\\(core\\): Codex task P2-C3"):
        redact_pii("sample text")
