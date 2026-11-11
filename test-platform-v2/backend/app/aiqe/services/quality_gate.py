"""M5 / TA-031：VersionTask Quality Gate（13 号 §19 TA-031）。

门禁只在 **P0 全部 PASS** 时显示 PASS：
- P0 有 FAIL → FAIL；
- P0 有 UNKNOWN / NOT_RUN → BLOCKED（绝不显示 PASS）；
- 没有 P0 → BLOCKED。
"""
from __future__ import annotations

from typing import Any

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"


def _result(
    *,
    p0_total: int,
    passed: int,
    failed: int,
    unknown: int,
    not_run: int,
    reasons: list[str],
) -> dict[str, Any]:
    if p0_total == 0:
        status = BLOCKED
        reasons = reasons or ["无 P0 用例，门禁不能判定为 PASS"]
    elif failed > 0:
        status = FAIL
    elif unknown > 0 or not_run > 0:
        status = BLOCKED
    elif passed == p0_total:
        status = PASS
    else:
        status = BLOCKED
        reasons = reasons or ["P0 未全部通过"]
    return {
        "gate_status": status,
        "p0_total": p0_total,
        "p0_passed": passed,
        "p0_failed": failed,
        "p0_unknown": unknown,
        "p0_not_run": not_run,
        "reasons": reasons,
    }


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    p0 = [case for case in cases if str(case.get("priority") or "").upper() == "P0"]
    statuses = [str(case.get("status") or "NOT_RUN").upper() for case in p0]
    passed = statuses.count("PASS")
    failed = statuses.count("FAIL")
    unknown = statuses.count("UNKNOWN")
    not_run = statuses.count("NOT_RUN") + statuses.count("PENDING")
    reasons: list[str] = []
    if failed:
        reasons.append(f"{failed} 条 P0 失败")
    if unknown:
        reasons.append(f"{unknown} 条 P0 未知")
    if not_run:
        reasons.append(f"{not_run} 条 P0 未执行")
    return _result(
        p0_total=len(p0),
        passed=passed,
        failed=failed,
        unknown=unknown,
        not_run=not_run,
        reasons=reasons,
    )


def evaluate_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """按聚合统计判定（P0 未执行/未知/失败均不得 PASS）。"""
    total = int(stats.get("p0_total") or 0)
    passed = int(stats.get("p0_passed") or 0)
    failed = int(stats.get("p0_failed") or 0)
    unknown = int(stats.get("p0_unknown") or 0)
    not_run = int(stats.get("p0_not_run") or 0)
    reasons: list[str] = []
    if failed:
        reasons.append(f"{failed} 条 P0 失败")
    if unknown:
        reasons.append(f"{unknown} 条 P0 未知")
    if not_run:
        reasons.append(f"{not_run} 条 P0 未执行")
    return _result(
        p0_total=total,
        passed=passed,
        failed=failed,
        unknown=unknown,
        not_run=not_run,
        reasons=reasons,
    )
