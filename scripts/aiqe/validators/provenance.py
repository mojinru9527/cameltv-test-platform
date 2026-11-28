"""Evidence provenance 校验（FIX-011）。

原始测试结果中的 ``tested_commit_sha`` 是事实源；Builder 传入的 PR Head /
merge SHA 只能作为并列字段，不得覆盖 tested SHA。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from statuses import PASS
from validators.common import is_sha, parse_time, resolve_repo_path, sha256_file
from validators.models import GateCheck

SHA_FIELDS = ("tested_commit_sha", "pr_head_sha", "merge_commit_sha", "release_target_sha")


def validate_provenance(
    payload: Any,
    *,
    expected_tested_sha: str = "",
    expected_release_sha: str = "",
    root: Path | None = None,
    require_pr_head: bool = False,
    require_container_digest: bool = False,
) -> GateCheck:
    check = GateCheck()
    if not isinstance(payload, dict) or not payload:
        return GateCheck.unproven("缺少 provenance / evidence index")
    source = payload.get("source") if isinstance(payload.get("source"), dict) else payload
    tested = str(source.get("tested_commit_sha") or "").strip().lower()
    if not is_sha(tested):
        check.add("缺少原始 tested_commit_sha（Builder 不得补写）")
    elif expected_tested_sha and tested != expected_tested_sha.strip().lower():
        check.add(
            f"tested_commit_sha={tested[:12]} 与实际 checkout {expected_tested_sha[:12]} 不一致"
        )
    pr_head = str(source.get("pr_head_sha") or "").strip().lower()
    if require_pr_head and not is_sha(pr_head):
        check.add("缺少 pr_head_sha")
    merge = str(source.get("merge_commit_sha") or "").strip().lower()
    release = str(source.get("release_target_sha") or "").strip().lower()
    for name, value in (("pr_head_sha", pr_head), ("merge_commit_sha", merge), ("release_target_sha", release)):
        if value and not is_sha(value):
            check.add(f"{name} 非法: {value!r}")
    if expected_release_sha and release and release != expected_release_sha.strip().lower():
        check.add(f"release_target_sha={release[:12]} 与本次签署 SHA 不一致")

    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    environment = str(runtime.get("environment") or payload.get("environment") or "").strip()
    if not environment:
        check.add("缺少 environment")
    elif environment.lower() in {"local", "localhost", "local-rehearsal"}:
        check.add(f"environment={environment} 为本地环境，不能替代目标环境 provenance")
    runtime_type = str(runtime.get("runtime_type") or "").strip()
    if runtime_type == "container" or require_container_digest:
        digest = str(runtime.get("driver_image_digest") or "").strip().lower()
        if not digest.startswith("sha256:") or len(digest) != 71:
            check.add("container Runner 缺少 immutable driver_image_digest")
    duration = runtime.get("duration_ms")
    try:
        duration_value = int(duration)
    except (TypeError, ValueError):
        duration_value = -1
    if duration_value <= 0:
        check.add(f"duration_ms={duration!r}，不能作为有效执行记录")
    started = parse_time(runtime.get("started_at"))
    finished = parse_time(runtime.get("finished_at"))
    if started is None or finished is None or finished < started:
        check.add("缺少有效 started_at/finished_at")

    workflow = payload.get("workflow") if isinstance(payload.get("workflow"), dict) else {}
    for field in ("run_id", "attempt", "job_id"):
        if str(workflow.get(field) or "").strip() == "":
            check.add(f"workflow 缺少 {field}")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        check.add("缺少 artifacts 清单（名称/hash/job）")
    elif root is not None:
        for item in artifacts:
            if not isinstance(item, dict):
                check.add("artifacts 含非对象条目")
                continue
            raw_path = item.get("path") or item.get("name")
            path = resolve_repo_path(root, raw_path)
            if path is None or not path.exists():
                check.add(f"artifact 不存在或越界: {raw_path!r}")
                continue
            expected_hash = str(item.get("sha256") or "").strip().lower().removeprefix("sha256:")
            if expected_hash and expected_hash != sha256_file(path):
                check.add(f"artifact {raw_path!r} sha256 不匹配")

    verification = payload.get("verification") if isinstance(payload.get("verification"), dict) else {}
    if verification.get("errors"):
        check.add(f"provenance verification 仍有错误: {verification.get('errors')}")

    if check.reasons:
        return check
    check.status = PASS
    check.note("provenance 一致：tested/head/merge/release SHA 分字段且 runtime 可追溯")
    return check


__all__ = ["SHA_FIELDS", "validate_provenance"]
