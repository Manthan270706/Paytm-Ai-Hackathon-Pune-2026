from typing import Any


class OpsSaathiError(Exception):
    """Base application exception."""

    def __init__(
        self, message: str, code: str = "INTERNAL_ERROR", details: Any | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class ConflictError(OpsSaathiError):
    """Raised when an optimistic concurrency or state version conflict occurs."""

    def __init__(
        self, message: str = "Version conflict detected", details: Any | None = None
    ) -> None:
        super().__init__(message=message, code="CONFLICT", details=details)


class ForbiddenError(OpsSaathiError):
    """Raised when an actor lacks permission or policy denies the action."""

    def __init__(self, message: str = "Action forbidden", details: Any | None = None) -> None:
        super().__init__(message=message, code="FORBIDDEN", details=details)


class NotFoundError(OpsSaathiError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: Any | None = None) -> None:
        super().__init__(message=message, code="NOT_FOUND", details=details)
