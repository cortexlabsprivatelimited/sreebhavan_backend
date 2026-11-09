"""In-memory sliding-window rate limiter, per client IP.

Good for a single API instance. When running several instances, swap the store for Redis.
"""

import asyncio
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        for header in ("cf-connecting-ip", "x-real-ip"):
            if v := request.headers.get(header):
                return v.strip()
        if fwd := request.headers.get("x-forwarded-for"):
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def hit(self, key: str) -> None:
        now = time.monotonic()
        async with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = int(q[0] + self.window - now) + 1
                raise AppError(
                    429,
                    "rate_limited",
                    "Too many enquiries from this device. Please try again later or call us.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)
            if len(self._hits) > 10_000:  # keep memory bounded
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= now - self.window]:
                    del self._hits[k]

    def reset(self) -> None:
        self._hits.clear()


_settings = get_settings()
enquiry_limiter = RateLimiter(_settings.enquiry_rate_limit, _settings.enquiry_rate_window_seconds)


async def limit_enquiries(request: Request) -> None:
    await enquiry_limiter.hit(client_ip(request))
