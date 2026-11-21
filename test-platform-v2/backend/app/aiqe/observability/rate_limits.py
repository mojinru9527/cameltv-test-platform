"""V16-024：AIQE 生产限流（launch / agent run / report）。

- 默认仅生产启用（`AIQE_RATE_LIMIT_ENFORCE=true` 可强制）；
- 桶按 project_id 隔离，避免单项目打爆全局；
- 超限返回 `RATE_LIMITED`，由调用方映射 429，不得静默放行。
"""
from __future__ import annotations

from app.core.config import settings
from app.core.rate_limit import RateLimiter


class RateLimited(RuntimeError):
    code = "RATE_LIMITED"

    def __init__(self, bucket: str, retry_after: int) -> None:
        super().__init__(f"RATE_LIMITED: {bucket} retry_after={retry_after}s")
        self.bucket = bucket
        self.retry_after = int(retry_after)


launch_limiter = RateLimiter(max_requests=30, window_seconds=60)
agent_run_limiter = RateLimiter(max_requests=10, window_seconds=60)
report_limiter = RateLimiter(max_requests=600, window_seconds=60)

_BUCKETS = {
    "launch": launch_limiter,
    "agent_run": agent_run_limiter,
    "report": report_limiter,
}


def _enforced() -> bool:
    return bool(settings.aiqe_rate_limit_enforce) or str(settings.environment) == "production"


def enforce(bucket: str, *, project_id: int | str, amount: int = 1) -> None:
    limiter = _BUCKETS.get(str(bucket))
    if limiter is None:
        raise KeyError(bucket)
    if not _enforced():
        return
    for _ in range(max(1, int(amount))):
        allowed, wait = limiter.is_allowed(f"{bucket}:{project_id}")
        if not allowed:
            raise RateLimited(str(bucket), wait)


__all__ = [
    "RateLimited",
    "agent_run_limiter",
    "enforce",
    "launch_limiter",
    "report_limiter",
]
