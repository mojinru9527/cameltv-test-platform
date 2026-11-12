"""M8 / TA-040：微信小程序 Adapter（minium / weapp-dev-mcp + 版本兼容矩阵）。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

WECHAT_MATRIX: dict[str, dict[str, Any]] = {
    "8.0.40": {"minium": True, "weapp_dev_mcp": False, "notes": "baseline"},
    "8.0.45": {"minium": False, "weapp_dev_mcp": True, "notes": "过渡版本"},
    "8.0.47": {"minium": True, "weapp_dev_mcp": True, "notes": "推荐"},
    "8.0.50": {"minium": True, "weapp_dev_mcp": True, "notes": "latest"},
}
BACKENDS = ("minium", "weapp_dev_mcp")


class MiniappError(ValueError):
    pass


def resolve_backend(version: str, preferred: str = "minium") -> str:
    if version not in WECHAT_MATRIX:
        raise MiniappError(f"未覆盖的微信版本: {version}")
    if preferred not in BACKENDS:
        raise MiniappError(f"未知后端: {preferred}")
    row = WECHAT_MATRIX[version]
    if row.get(preferred):
        return preferred
    for backend in BACKENDS:
        if row.get(backend):
            return backend
    raise MiniappError(f"版本 {version} 无可用后端")


@dataclass(frozen=True)
class MiniappCase:
    case_id: str
    title: str
    page: str
    expected: str


CASES: tuple[MiniappCase, ...] = (
    MiniappCase("MP-001", "首页加载", "pages/index/index", "首页可见"),
    MiniappCase("MP-002", "直播列表", "pages/live/list", "列表有数据"),
    MiniappCase("MP-003", "赛事详情", "pages/match/detail", "比分展示"),
    MiniappCase("MP-004", "收藏操作", "pages/live/detail", "收藏状态变化"),
    MiniappCase("MP-005", "分享卡片", "pages/match/detail", "分享参数正确"),
)


class MiniappAdapter:
    def __init__(self, executor: Callable[[MiniappCase], dict[str, Any]]) -> None:
        self.executor = executor

    def run(self) -> dict[str, Any]:
        results = []
        for case in CASES:
            outcome = self.executor(case) or {}
            passed = bool(outcome.get("passed"))
            results.append(
                {
                    "case_id": case.case_id,
                    "title": case.title,
                    "page": case.page,
                    "passed": passed,
                    "evidence": list(outcome.get("evidence") or []),
                    "error": str(outcome.get("error") or ""),
                }
            )
        passed_count = sum(1 for item in results if item["passed"])
        return {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "all_passed": passed_count == len(results),
            "results": results,
        }
