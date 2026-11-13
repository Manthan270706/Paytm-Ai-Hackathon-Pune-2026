import time
from collections import defaultdict

from fastapi import Request

from app.core.exceptions import RateLimitError


class InMemoryRateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int | None = None) -> None:
        limit = max_requests if max_requests is not None else self.max_requests
        now = time.time()
        window_start = now - self.window_seconds

        # Prune timestamps outside window
        valid_requests = [t for t in self.requests[key] if t > window_start]
        self.requests[key] = valid_requests

        if len(valid_requests) >= limit:
            raise RateLimitError(
                message=f"Rate limit exceeded: maximum {limit} requests per {self.window_seconds}s."
            )

        self.requests[key].append(now)

    def reset(self) -> None:
        self.requests.clear()


rate_limiter = InMemoryRateLimiter(max_requests=120, window_seconds=60)


async def check_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    rate_limiter.check(client_host)
