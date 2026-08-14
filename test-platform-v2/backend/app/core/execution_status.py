"""执行状态统一词表与规范化（FIX-173-P1-06 / Batch 182）。

历史：同一执行事实在 5 张表 4 套词表（pass/fail/skip/block、success、
done/fail、completed/failed、passed/failed/skipped），聚合层被迫逐表映射。
Batch 182 统一为单一规范值集合：

    pending | running | passed | failed | skipped | cancelled | blocked

- 新代码只写规范值；
- `canonical_exec_status(v)` 兼容历史旧值（pass/fail/skip/block/success/done/completed），
  供 open_api 回写（CI 契约向后兼容）与过渡期读取使用；
- 前端经 `frontend/src/utils/executionStatus.ts` 展示（新旧双值兼容）。
"""
from __future__ import annotations

# 规范状态值（DB 唯一词表）
PENDING = "pending"
RUNNING = "running"
PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"
CANCELLED = "cancelled"
BLOCKED = "blocked"

CANONICAL_STATUSES = frozenset({PENDING, RUNNING, PASSED, FAILED, SKIPPED, CANCELLED, BLOCKED})

# 旧值 → 规范值（历史数据/外部契约兼容映射）
_LEGACY_MAP = {
    "pass": PASSED,
    "fail": FAILED,
    "skip": SKIPPED,
    "block": BLOCKED,
    "success": PASSED,
    "done": PASSED,
    "completed": PASSED,
}


def canonical_exec_status(value: str | None) -> str:
    """把任意历史/外部状态值规范化为统一词表；未知值原样返回。

    open_api 回写等外部入口必须经本函数后落库，保证 CI 旧脚本（pass/fail/skip/block）
    与新值并存期间行为一致。
    """
    if not value:
        return value or ""
    if value in CANONICAL_STATUSES:
        return value
    return _LEGACY_MAP.get(value, value)
