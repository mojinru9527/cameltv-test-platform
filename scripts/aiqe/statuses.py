"""V1.6.2 统一状态语义（单一事实源）。

任何 Gate、TC、阶段、审计条目的状态都必须来自这里，禁止各脚本自行定义
"半自动=通过"、"WAIVED=通过" 等折算规则。只有 ``PASS`` 计入通过。
"""
from __future__ import annotations

from collections.abc import Iterable

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
NOT_RUN = "NOT_RUN"
NOT_PROVEN = "NOT_PROVEN"
PARTIAL = "PARTIAL"
WAIVED = "WAIVED"
UNKNOWN = "UNKNOWN"

STATUSES: tuple[str, ...] = (
    PASS,
    FAIL,
    BLOCKED,
    NOT_RUN,
    NOT_PROVEN,
    PARTIAL,
    WAIVED,
    UNKNOWN,
)

# 旧状态只允许降级映射，不得映射为 PASS。
LEGACY_STATUS_MAP: dict[str, str] = {
    "SEMI_AUTOMATIC": PARTIAL,
    "SEMI-AUTOMATIC": PARTIAL,
    "MANUAL": PARTIAL,
    "SCREENSHOT": PARTIAL,
    "SCREENSHOT_ONLY": PARTIAL,
    "SKIPPED": NOT_RUN,
    "SKIP": NOT_RUN,
    "PENDING": NOT_RUN,
    "TODO": NOT_RUN,
    "IN_PROGRESS": BLOCKED,
    "RUNNING": BLOCKED,
    "QUEUED": NOT_RUN,
    "ERROR": FAIL,
    "FAILED": FAIL,
    "OK": PASS,
    "SUCCESS": PASS,
    "VERIFIED": PASS,
}

# 聚合时的严重度：值越小越严重。FAIL 优先于 BLOCKED，避免真实失败被环境原因覆盖。
_SEVERITY = {
    FAIL: 0,
    BLOCKED: 1,
    NOT_PROVEN: 2,
    PARTIAL: 3,
    UNKNOWN: 4,
    NOT_RUN: 5,
    WAIVED: 6,
    PASS: 7,
}


def normalize(raw: object, *, empty: str = NOT_RUN) -> str:
    """把任意输入归一化为合法状态；无法识别时返回 ``UNKNOWN``（阻断）。"""
    text = str(raw or "").strip().upper().replace(" ", "_")
    if not text:
        return empty
    if text in STATUSES:
        return text
    return LEGACY_STATUS_MAP.get(text, UNKNOWN)


def is_pass(raw: object) -> bool:
    return normalize(raw) == PASS


def aggregate(values: Iterable[object], *, empty: str = NOT_PROVEN) -> str:
    """按最弱覆盖原则聚合状态：任一 FAIL → FAIL；任一非 PASS → 最严重者。"""
    items = [normalize(value) for value in values]
    if not items:
        return empty
    return min(items, key=lambda item: _SEVERITY[item])


def counts(values: Iterable[object]) -> dict[str, int]:
    result = {status: 0 for status in STATUSES}
    for value in values:
        result[normalize(value)] += 1
    return result


def describe(status: str) -> str:
    return {
        PASS: "正式入口执行完成、强制业务断言通过、证据完整",
        FAIL: "已执行且至少一个强制业务断言失败",
        BLOCKED: "环境/Runner/外部依赖导致无法执行",
        NOT_RUN: "本次没有执行",
        NOT_PROVEN: "有记录但缺少证明结论所需的关键证据",
        PARTIAL: "仅覆盖部分平台或步骤",
        WAIVED: "经授权豁免，不代表执行通过",
        UNKNOWN: "无法可靠判断，按阻断处理",
    }[normalize(status)]


__all__ = [
    "BLOCKED",
    "FAIL",
    "LEGACY_STATUS_MAP",
    "NOT_PROVEN",
    "NOT_RUN",
    "PARTIAL",
    "PASS",
    "STATUSES",
    "UNKNOWN",
    "WAIVED",
    "aggregate",
    "counts",
    "describe",
    "is_pass",
    "normalize",
]
