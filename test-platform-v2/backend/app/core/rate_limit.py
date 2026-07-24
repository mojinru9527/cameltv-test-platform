"""Lightweight in-memory rate limiter for Open API endpoints.

Uses a sliding-window counter per token_hash, 60 req/min default.
No external dependency (Redis is overkill for current scale).
State is lost on restart — acceptable for v2.3, documented limitation.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Sliding-window rate limiter with per-key counters."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counters: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_seconds
        self._counters[key] = [t for t in self._counters[key] if t > cutoff]
        if not self._counters[key]:
            del self._counters[key]

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """Check if the key can make another request.

        Returns (allowed, remaining_seconds_until_reset).
        """
        now = time.time()
        with self._lock:
            self._prune(key, now)
            if len(self._counters[key]) >= self.max_requests:
                # Calculate time until oldest entry expires
                oldest = min(self._counters[key])
                wait = int(oldest + self.window_seconds - now) + 1
                return False, max(1, wait)
            self._counters[key].append(now)
            return True, 0

    def cleanup(self) -> int:
        """Remove stale entries. Call periodically. Returns keys removed."""
        now = time.time()
        removed = 0
        with self._lock:
            stale = [k for k in list(self._counters.keys()) if not self._counters[k]]
            for k in stale:
                del self._counters[k]
                removed += 1
            for k in list(self._counters.keys()):
                self._prune(k, now)
                if k not in self._counters:
                    removed += 1
        return removed


# Singleton for open API endpoints
open_api_limiter = RateLimiter(max_requests=60, window_seconds=60)

# Login rate limiter: max 10 attempts per IP per 15 min
login_limiter = RateLimiter(max_requests=10, window_seconds=900)
