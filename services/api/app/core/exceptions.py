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


class UnauthorizedError(OpsSaathiError):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(
        self, message: str = "Authentication required", details: Any | None = None
    ) -> None:
        super().__init__(message=message, code="UNAUTHORIZED", details=details)


class ForbiddenError(OpsSaathiError):
    """Raised when an actor lacks permission or policy denies the action."""

    def __init__(self, message: str = "Action forbidden", details: Any | None = None) -> None:
        super().__init__(message=message, code="FORBIDDEN", details=details)


class NotFoundError(OpsSaathiError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: Any | None = None) -> None:
        super().__init__(message=message, code="NOT_FOUND", details=details)


class ConflictError(OpsSaathiError):
    """Raised when an optimistic concurrency or state version conflict occurs."""

    def __init__(
        self, message: str = "Version conflict detected", details: Any | None = None
    ) -> None:
        super().__init__(message=message, code="CONFLICT", details=details)


class ValidationError(OpsSaathiError):
    """Raised when client input or parameter validation fails."""

    def __init__(self, message: str = "Validation failed", details: Any | None = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)


class RateLimitError(OpsSaathiError):
    """Raised when client exceeds rate limits."""

    def __init__(
        self, message: str = "Too many requests. Please slow down.", details: Any | None = None
    ) -> None:
        super().__init__(message=message, code="RATE_LIMITED", details=details)
