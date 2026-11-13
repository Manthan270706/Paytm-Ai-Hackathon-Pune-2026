import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = "SYNTHETIC_DEMO"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class APIError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class APIResponse(BaseModel, Generic[T]):
    ok: bool = True
    data: T | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    error: APIError | None = None


def success_response(
    data: Any, source_type: str = "SYNTHETIC_DEMO", request_id: str | None = None
) -> dict[str, Any]:
    meta = ResponseMeta(
        request_id=request_id or str(uuid.uuid4()),
        source_type=source_type,
        timestamp=datetime.now(UTC).isoformat(),
    )
    return {"ok": True, "data": data, "meta": meta.model_dump(), "error": None}


def error_response(
    code: str,
    message: str,
    details: Any | None = None,
    source_type: str = "SYNTHETIC_DEMO",
    request_id: str | None = None,
) -> dict[str, Any]:
    meta = ResponseMeta(
        request_id=request_id or str(uuid.uuid4()),
        source_type=source_type,
        timestamp=datetime.now(UTC).isoformat(),
    )
    return {
        "ok": False,
        "data": None,
        "meta": meta.model_dump(),
        "error": {"code": code, "message": message, "details": details},
    }
