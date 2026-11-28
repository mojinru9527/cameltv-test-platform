"""Runtime Evidence Index 语义校验（FIX-001 / FIX-011）。

只读原始 ``evidence-index.json``；不仅检查 ``summary.ga_ready`` 的 key，
而是逐条验证每一条 PASS 的追溯链、SHA、环境、时间与 artifact 引用。
"""
from __future__ import annotations

from typing import Any

from statuses import BLOCKED, FAIL, NOT_PROVEN, NOT_RUN, PASS
from validators.common import duration_ms, is_digest, is_sha, parse_time
from validators.models import GateCheck

LOCAL_ENVIRONMENTS = {"local", "localhost", "local-rehearsal", "local-test", "dev", "development"}


def _has(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def validate_runtime_index(
    payload: Any,
    *,
    expected_commit: str | None = None,
    expected_environment: str | None = None,
    allow_local: bool = False,
    require_platform_tcs: int = 0,
) -> GateCheck:
    check = GateCheck()
    check.status = PASS
    if not isinstance(payload, dict) or not payload:
        return GateCheck.unproven("缺少 Runtime Evidence Index 或格式非法")

    commit = str(payload.get("commit_sha") or "").strip().lower()
    if not is_sha(commit):
        check.add(f"Runtime index commit_sha 非法: {commit or '<empty>'}")
    elif expected_commit and commit != str(expected_commit).strip().lower():
        check.add(f"Runtime index commit_sha {commit[:12]} 与实际验收 SHA {str(expected_commit)[:12]} 不一致")

    environment = str(payload.get("environment") or "").strip()
    if not environment:
        check.add("Runtime index environment 为空")
    elif not allow_local and environment.lower() in LOCAL_ENVIRONMENTS:
        check.add(f"Runtime index environment={environment}，本地演练不能替代目标环境验收")
    elif expected_environment and environment != expected_environment:
        check.add(f"Runtime index environment={environment} 与要求 {expected_environment} 不一致")

    ci_run = str(payload.get("ci_run_id") or "").strip()
    if not ci_run:
        check.add("Runtime index 缺少 ci_run_id")
    elif not allow_local and (ci_run.startswith("local") or ci_run.lower() in {"0", "none"}):
        check.add(f"Runtime index ci_run_id={ci_run}，不是真实 CI 执行身份")

    generated = parse_time(payload.get("generated_at"))
    if generated is None:
        check.add("Runtime index 缺少可解析的 generated_at")

    tests = payload.get("tests") or []
    if not isinstance(tests, list) or not tests:
        return GateCheck.unproven("Runtime index 没有 tests 记录", evidence=check.reasons)

    seen: set[str] = set()
    passed = 0
    for index, item in enumerate(tests, 1):
        if not isinstance(item, dict):
            check.add(f"Runtime index 第 {index} 条不是对象")
            continue
        tc_id = str(item.get("tc_id") or "").strip()
        if not tc_id:
            check.add(f"Runtime index 第 {index} 条缺少 tc_id")
        if tc_id in seen:
            check.add(f"Runtime index 重复 TC: {tc_id}")
        seen.add(tc_id)
        status = str(item.get("status") or "").strip().upper()
        if status != PASS:
            if status == FAIL:
                check.demote(FAIL)
                check.add(f"{tc_id}: FAIL 不得计入运行证据通过")
            elif status in {BLOCKED, NOT_RUN}:
                check.demote(NOT_PROVEN)
                check.add(f"{tc_id}: {status} 不得计入运行证据通过")
            else:
                check.add(f"{tc_id}: 非法状态 {status!r}")
            continue
        passed += 1
        missing = [
            key
            for key, value in {
                "run_id": item.get("run_id"),
                "project_id": item.get("project_id"),
                "workflow_snapshot_hash": item.get("workflow_snapshot_hash"),
                "job_ids": item.get("job_ids"),
                "node_run_ids": item.get("node_run_ids"),
                "assertion_ids": item.get("assertion_ids"),
                "artifact_refs": item.get("artifact_refs"),
            }.items()
            if not _has(value)
        ]
        if missing:
            check.add(f"{tc_id}: PASS 缺少追溯链字段 {missing}")
        snapshot = str(item.get("workflow_snapshot_hash") or "")
        if snapshot and not is_digest("sha256:" + snapshot) and not is_sha(snapshot):
            if len(snapshot) != 64:
                check.add(f"{tc_id}: workflow_snapshot_hash 非法")
        runtime_type = str(item.get("runtime_type") or payload.get("runtime_type") or "container").lower()
        digest = str(item.get("driver_image_digest") or "").strip()
        if runtime_type == "container" and not is_digest(digest):
            check.add(f"{tc_id}: container Runner 缺少 immutable driver_image_digest")
        duration = item.get("duration_ms")
        try:
            duration_value = int(duration)
        except (TypeError, ValueError):
            duration_value = -1
        if duration_value <= 0:
            check.add(f"{tc_id}: duration_ms={duration!r}，不能作为有效真实执行记录")
        started = item.get("started_at")
        finished = item.get("finished_at")
        if started or finished:
            measured = duration_ms(started, finished)
            if measured is None:
                check.add(f"{tc_id}: started_at/finished_at 缺失或无法计算")
            elif duration_value > 0 and abs(measured - duration_value) > max(2000, duration_value // 10):
                check.add(f"{tc_id}: duration_ms={duration_value} 与时间跨度 {measured}ms 不一致")

    if require_platform_tcs and len(tests) < int(require_platform_tcs):
        check.add(f"Runtime index TC 数量 {len(tests)} < {require_platform_tcs}")

    summary = payload.get("summary") or {}
    if not isinstance(summary, dict):
        check.add("Runtime index summary 缺失或格式非法")
        summary = {}
    if summary.get("ga_ready") is not True:
        check.add(f"Runtime index summary.ga_ready 不为 true: {summary.get('ga_ready')!r}")
    for key in ("FAIL", "BLOCKED", "NOT_RUN"):
        count = int(summary.get(key) or 0)
        if count:
            check.add(f"Runtime index summary.{key}={count}，阻断 GA")
    if int(summary.get("PASS") or 0) != passed:
        check.add(
            f"Runtime index summary.PASS={summary.get('PASS')} 与逐条 PASS={passed} 不一致"
        )
    if int(summary.get("total") or 0) != len(tests):
        check.add(f"Runtime index summary.total={summary.get('total')} 与 tests={len(tests)} 不一致")

    if check.status == PASS:
        check.note("Runtime index 逐条追溯链、SHA、环境与时间校验通过")
        check.evidence_refs.append("docs/aiqe/v1.6/evidence/evidence-index.json")
    return check


__all__ = ["validate_runtime_index"]
