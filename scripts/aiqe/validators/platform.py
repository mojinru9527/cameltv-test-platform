"""平台链路机器结果校验（TC-PLATFORM-*，Gate E 的组成部分）。

平台链路 PASS 与产品 TC PASS 是两个命名空间；平台链路用于证明执行链基础设施，
不能替代产品 TC。这里只校验平台结果本身的可信度，不把它当作产品验收。
"""
from __future__ import annotations

from typing import Any

from statuses import FAIL, PASS
from validators.common import is_digest, is_sha
from validators.models import GateCheck

LOCAL_ENVIRONMENTS = {"local", "localhost", "local-rehearsal", "local-test", "dev", "development"}


def validate_platform_results(
    payload: Any,
    *,
    expected_commit: str = "",
    expected_environment: str = "",
    allow_local: bool = False,
    require_tcs: int = 10,
) -> GateCheck:
    check = GateCheck()
    check.status = PASS
    if not isinstance(payload, dict) or not payload:
        return GateCheck.unproven("缺少 platform-results.json")
    commit = str(payload.get("commit_sha") or "").strip().lower()
    if not is_sha(commit):
        check.add("platform-results commit_sha 非法")
    elif expected_commit and commit != expected_commit.strip().lower():
        check.add(f"platform-results commit={commit[:12]} 与验收 SHA {expected_commit[:12]} 不一致")
    environment = str(payload.get("environment") or "").strip()
    if not environment:
        check.add("platform-results 缺少 environment")
    elif not allow_local and environment.lower() in LOCAL_ENVIRONMENTS:
        check.add(f"platform-results environment={environment}，本地结果不能计入目标环境验收")
    elif expected_environment and environment != expected_environment:
        check.add(f"platform-results environment={environment} 与要求 {expected_environment} 不一致")
    ci_run = str(payload.get("ci_run") or "").strip()
    if not ci_run:
        check.add("platform-results 缺少 CI run 身份")
    elif not allow_local and ci_run.lower() in {"local", "none", "0"}:
        check.add(f"platform-results ci_run={ci_run!r} 不是真实 CI 执行")

    tests = payload.get("tests") or []
    if not isinstance(tests, list) or not tests:
        return GateCheck.unproven("platform-results 没有 tests")
    if require_tcs and len(tests) < int(require_tcs):
        check.add(f"platform-results TC 数量 {len(tests)} < {require_tcs}")
    seen: set[str] = set()
    for item in tests:
        if not isinstance(item, dict):
            check.add("platform-results 含非对象条目")
            continue
        tc_id = str(item.get("tc_id") or "?").strip()
        if tc_id in seen:
            check.add(f"platform-results 重复 TC: {tc_id}")
        seen.add(tc_id)
        status = str(item.get("status") or "").strip().upper()
        if status != PASS:
            if status == FAIL:
                check.demote(FAIL)
            check.add(f"{tc_id}: {status or '<empty>'} 不能计入平台链路 PASS")
            continue
        run_status = str(item.get("run_status") or "").strip().upper()
        run_outcome = str(item.get("run_outcome") or "").strip().upper()
        if run_status != "COMPLETED":
            check.add(f"{tc_id}: run_status={run_status or '<empty>'}，未到终态")
        if run_outcome != PASS:
            check.add(f"{tc_id}: run_outcome={run_outcome or '<empty>'}，与 status=PASS 矛盾")
        for key in ("run_id", "project_id", "job_ids", "node_run_ids", "assertion_ids", "artifact_refs"):
            value = item.get(key)
            if not value:
                check.add(f"{tc_id}: PASS 缺少 {key}")
        try:
            duration_value = int(item.get("duration_ms"))
        except (TypeError, ValueError):
            duration_value = -1
        if duration_value <= 0:
            check.add(f"{tc_id}: duration_ms={item.get('duration_ms')!r}，不是有效执行记录")
        if not allow_local:
            digest = str(item.get("driver_image_digest") or "").strip().lower()
            if not is_digest(digest):
                check.add(f"{tc_id}: container Runner 缺少 immutable driver_image_digest")

    if check.status == PASS:
        check.note(f"平台链路 {len(tests)} 条结果语义一致")
        check.evidence_refs.append("docs/aiqe/v1.6/e2e/platform-results.json")
    return check


__all__ = ["validate_platform_results"]
