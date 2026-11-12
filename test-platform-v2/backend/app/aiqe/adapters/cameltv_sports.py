"""M6 / TA-034：CamelTv Sports 纵向验收 adapter（TC-AIQE-001..010）。

执行器由调用方注入（真实节点/UI 或测试 fake）；本模块只固化 10 条纵向场景契约与汇总。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SportsCase:
    case_id: str
    title: str
    steps: tuple[str, ...]
    expected: str


CASES: tuple[SportsCase, ...] = (
    SportsCase("TC-AIQE-001", "直播入口可见", ("打开首页", "进入直播 tab"), "入口卡片可见"),
    SportsCase("TC-AIQE-002", "直播起播", ("点击直播卡片", "等待播放器"), "3s 内起播"),
    SportsCase("TC-AIQE-003", "暂停/恢复", ("点击暂停", "点击恢复"), "播放状态正确切换"),
    SportsCase("TC-AIQE-004", "清晰度切换", ("打开清晰度菜单", "选择 720p"), "码率与画面切换"),
    SportsCase("TC-AIQE-005", "收藏直播", ("点击收藏", "刷新页面"), "收藏状态保持"),
    SportsCase("TC-AIQE-006", "搜索赛事", ("输入球队名", "查看结果"), "命中目标赛事"),
    SportsCase("TC-AIQE-007", "断流重连", ("模拟断流", "等待重连"), "5s 内恢复播放"),
    SportsCase("TC-AIQE-008", "赛事详情比分", ("打开赛果页", "对比比分"), "比分与数据源一致"),
    SportsCase("TC-AIQE-009", "分享链接", ("点击分享", "打开链接"), "落地页可播放"),
    SportsCase("TC-AIQE-010", "弱网降级", ("限速 3G", "进入直播"), "降级提示且可播放"),
)


class SportsVerticalAdapter:
    def __init__(self, executor: Callable[[SportsCase], dict[str, Any]]) -> None:
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
