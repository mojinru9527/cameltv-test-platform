"""V16-023 / FIX-011：从 Runtime E2E 机器结果生成 evidence-index.json。

原则（V1.6.2 加固）
------------------
1. **原始执行结果是事实源。** 输入 JSON 里的 ``commit_sha`` / ``tested_commit_sha``
   是测试进程实际 checkout 并运行的 SHA；Builder 只能原样保留，不能覆盖。
   若同时通过 ``--commit-sha`` / ``--tested-commit-sha`` 传入不同 SHA，直接
   ``EvidenceError``（非零退出），绝不静默改写。
2. **SHA 分字段。** ``source`` 同时记录 ``tested_commit_sha`` / ``pr_head_sha`` /
   ``merge_commit_sha`` / ``release_target_sha``；它们可以不同，但不得互相覆盖。
3. **environment 必须来自真实运行事实。** 缺失或本地环境（``local`` /
   ``local-*`` / ``dev``）不能作为 GA 运行时证据；artifact 与命令行声明冲突时
   保留 artifact 原始值并记录 ``verification.errors``。
4. **时间必须可追溯。** ``duration_ms`` 缺失时由 ``started_at``/``finished_at``
   计算；两者冲突时保留原始值、记录计算值与错误，不静默覆盖。
5. **artifacts 只汇总不臆造。** 清单保存 ``name/path/sha256/job_id``；文件是否
   存在、hash 是否匹配由调用方 / validator（``validators.provenance``）校验。
6. PASS 必须具备完整追溯链：commit SHA、CI Run、环境、Run ID、Project、
   WorkflowSnapshot hash、Job IDs、NodeRun IDs、Assertion IDs、Artifact refs。
7. BLOCKED/NOT_RUN 不计入通过率，必须给原因；重复 TC、缺失 ID、伪造 ID 一律非零退出。

输出结构见 ``docs/aiqe/v1.6`` 下 evidence-index；新增 ``source`` / ``runtime`` /
``workflow`` / ``artifacts`` / ``verification`` 区块，供
``validators.provenance`` 与 ``validators.runtime_index`` 校验。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover - 脚本/测试两条加载路径
    sys.path.insert(0, str(SCRIPT_DIR))
from validators.common import duration_ms as _duration_ms  # noqa: E402
from validators.common import is_digest, is_sha, parse_time  # noqa: E402

HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
TC_RE = re.compile(r"^TC-[A-Z0-9]+-\d{3}$")
LOCAL_ENVIRONMENT_RE = re.compile(r"^(?:local|localhost|local[-_].*|dev|development)$", re.IGNORECASE)
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
RUNTIME_TYPES = {"container", "host", "hosted", "browser", "external"}
REQUIRED_PASS_IDS = (
    "run_id",
    "project_id",
    "workflow_snapshot_hash",
    "job_ids",
    "node_run_ids",
    "assertion_ids",
    "artifact_refs",
)
DURATION_TOLERANCE_MS = 2000
ARTIFACT_FIELDS = ("name", "path", "sha256", "job_id")


class EvidenceError(ValueError):
    pass


def _nonempty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _first(declared: Any, flag: Any) -> tuple[str, bool]:
    """返回（生效值, 是否冲突）。original（artifact）优先，flag 只补充不覆盖。"""
    left, right = _text(declared), _text(flag)
    if left and right and left != right:
        return left, True
    return (left or right), False


def _parse_reported_duration(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_local_environment(environment: str) -> bool:
    return bool(LOCAL_ENVIRONMENT_RE.match(environment.strip()))


def _declared_facts(payload: Any) -> dict[str, Any]:
    """从原始 artifact 中提取“测试进程自己记录的”事实，缺省为空。"""
    if not isinstance(payload, dict):
        return {}
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    workflow = payload.get("workflow") if isinstance(payload.get("workflow"), dict) else {}
    return {
        "tested_commit_sha": _text(
            source.get("tested_commit_sha")
            or payload.get("tested_commit_sha")
            or payload.get("commit_sha")
        ),
        "pr_head_sha": _text(source.get("pr_head_sha") or payload.get("pr_head_sha")),
        "merge_commit_sha": _text(source.get("merge_commit_sha") or payload.get("merge_commit_sha")),
        "release_target_sha": _text(
            source.get("release_target_sha") or payload.get("release_target_sha")
        ),
        "environment": _text(runtime.get("environment") or payload.get("environment")),
        "runtime_type": _text(runtime.get("runtime_type") or payload.get("runtime_type")),
        "driver_image_digest": _text(
            runtime.get("driver_image_digest") or payload.get("driver_image_digest")
        ),
        "started_at": _text(runtime.get("started_at") or payload.get("started_at")),
        "finished_at": _text(runtime.get("finished_at") or payload.get("finished_at")),
        "duration_ms": runtime.get("duration_ms")
        if "duration_ms" in runtime
        else payload.get("duration_ms"),
        "run_id": _text(
            workflow.get("run_id") or payload.get("ci_run_id") or payload.get("ci_run")
        ),
        "attempt": _text(workflow.get("attempt") or payload.get("workflow_attempt")),
        "job_id": _text(workflow.get("job_id") or payload.get("job_id")),
    }


def _normalize_artifact(raw: Any, *, tc_id: str, default_job_id: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        name = _text(raw.get("name") or raw.get("artifact_id") or raw.get("path"))
        path = _text(raw.get("path") or raw.get("ref") or raw.get("file"))
        sha256 = _text(raw.get("sha256") or raw.get("hash")).lower().removeprefix("sha256:")
        job_id = raw.get("job_id") if raw.get("job_id") is not None else default_job_id
        entry = {
            "tc_id": tc_id,
            "name": name or path,
            "path": path or None,
            "sha256": sha256 or None,
            "job_id": job_id,
        }
        if raw.get("kind"):
            entry["kind"] = _text(raw.get("kind"))
        return entry
    reference = _text(raw)
    looks_like_path = "/" in reference or "\\" in reference
    return {
        "tc_id": tc_id,
        "name": reference,
        "path": reference.replace("\\", "/") if looks_like_path else None,
        "sha256": None,
        "job_id": default_job_id,
    }


def validate_record(
    record: dict,
    *,
    index: int,
    errors: list[str] | None = None,
) -> dict:
    """校验并规范化单条 TC 结果；不修改输入、不静默补写事实。"""
    record_errors = errors if errors is not None else []
    tc_id = str(record.get("tc_id") or "").strip()
    if not TC_RE.match(tc_id):
        raise EvidenceError(f"#{index}: tc_id 非法 {tc_id!r}")
    status = str(record.get("status") or "").strip().upper()
    if status not in STATUSES:
        raise EvidenceError(f"{tc_id}: 非法状态 {status!r}")
    job_ids = list(record.get("job_ids") or [])
    default_job = job_ids[0] if job_ids else None
    started_at = _text(record.get("started_at"))
    finished_at = _text(record.get("finished_at"))
    computed = _duration_ms(started_at, finished_at)
    reported = _parse_reported_duration(record.get("duration_ms"))
    if reported is None or reported <= 0:
        if computed is not None and computed > 0:
            effective_duration, duration_source = computed, "computed"
        else:
            effective_duration, duration_source = int(reported or 0), "missing"
            if status == "PASS":
                record_errors.append(
                    f"{tc_id}: duration_ms 缺失且无法由 started_at/finished_at 计算，"
                    "不能作为真实执行记录"
                )
    else:
        effective_duration, duration_source = reported, "runner"
        if computed is not None and abs(computed - reported) > max(
            DURATION_TOLERANCE_MS, reported // 10
        ):
            record_errors.append(
                f"{tc_id}: duration_ms={reported} 与起止时间跨度 {computed}ms 冲突，保留原始值 {reported}"
            )
    if status == "PASS" and (started_at or finished_at) and computed is None:
        record_errors.append(f"{tc_id}: started_at/finished_at 缺失或不合法，无法校验执行时长")

    raw_artifacts = list(record.get("artifacts") or [])
    raw_refs = list(record.get("artifact_refs") or [])
    artifacts: list[dict[str, Any]] = []
    seen_artifacts: set[tuple[str, str]] = set()
    for raw in raw_artifacts:
        entry = _normalize_artifact(raw, tc_id=tc_id, default_job_id=default_job)
        key = (entry["name"], str(entry["path"]))
        if key not in seen_artifacts:
            seen_artifacts.add(key)
            artifacts.append(entry)
    out = {
        "tc_id": tc_id,
        "status": status,
        "run_id": record.get("run_id") or None,
        "project_id": int(record["project_id"]) if record.get("project_id") else None,
        "workflow_snapshot_hash": record.get("workflow_snapshot_hash") or "",
        "job_ids": job_ids,
        "node_run_ids": list(record.get("node_run_ids") or []),
        "assertion_ids": list(record.get("assertion_ids") or []),
        # 兼容旧字段：artifact_refs 保存原始 ID/路径引用，不退化成“证据已存在”。
        "artifact_refs": raw_refs,
        "artifacts": artifacts,
        "driver_image_digest": _text(record.get("driver_image_digest")),
        "blocked_reason": _text(record.get("blocked_reason")),
        "duration_ms": effective_duration,
        "reported_duration_ms": reported,
        "computed_duration_ms": computed,
        "duration_source": duration_source,
        "started_at": started_at or None,
        "finished_at": finished_at or None,
    }
    if status == "PASS":
        evidence_refs = out["artifact_refs"] or out["artifacts"]
        missing = [
            key
            for key in REQUIRED_PASS_IDS
            if key == "project_id" and not out["project_id"]
            or key == "artifact_refs" and not _nonempty(evidence_refs)
            or key not in {"project_id", "artifact_refs"} and not _nonempty(out[key])
        ]
        if missing:
            raise EvidenceError(f"{tc_id}: PASS 缺少追溯 ID: {missing}")
        if not HASH_RE.match(str(out["workflow_snapshot_hash"])):
            raise EvidenceError(f"{tc_id}: workflow_snapshot_hash 非法")
    if status in {"BLOCKED", "NOT_RUN"} and not out["blocked_reason"]:
        raise EvidenceError(f"{tc_id}: BLOCKED/NOT_RUN 必须给出原因")
    return out


def build_index(
    *,
    tests: list[dict],
    ci_run_id: str,
    environment: str,
    commit_sha: str = "",
    tested_commit_sha: str = "",
    require_tcs: int = 0,
    pr_head_sha: str = "",
    merge_commit_sha: str = "",
    release_target_sha: str = "",
    runtime_type: str = "",
    driver_image_digest: str = "",
    started_at: str = "",
    finished_at: str = "",
    workflow_attempt: str = "",
    workflow_job_id: str = "",
    input_payload: dict | None = None,
    source_artifact: dict | None = None,
) -> dict:
    """汇总原始执行结果；只校验/记录事实，不覆盖 tested SHA 与环境。"""
    declared = _declared_facts(input_payload)
    errors: list[str] = []

    # ---------------- source：tested SHA 是事实源，禁止覆盖 ----------------
    flag_sha_raw, flag_sha_conflict = _first(tested_commit_sha, commit_sha)
    if flag_sha_conflict:
        raise EvidenceError(
            "同时传入 --tested-commit-sha 与 --commit-sha 且不一致，拒绝猜测测试事实"
        )
    declared_sha = declared.get("tested_commit_sha") or ""
    tested, tested_conflict = _first(declared_sha, flag_sha_raw)
    if tested_conflict:
        raise EvidenceError(
            "输入 artifact 记录的 tested_commit_sha="
            f"{declared_sha} 与传入 {flag_sha_raw} 不一致；Builder 不得覆盖原始 tested SHA"
        )
    tested_sha = tested.lower()
    if not is_sha(tested_sha):
        raise EvidenceError("缺少合法原始 tested_commit_sha（输入 artifact 或 --tested-commit-sha 必须提供）")

    head, head_conflict = _first(declared.get("pr_head_sha"), pr_head_sha)
    merge, merge_conflict = _first(declared.get("merge_commit_sha"), merge_commit_sha)
    release, release_conflict = _first(
        declared.get("release_target_sha"), release_target_sha
    )
    for label, value, conflict in (
        ("pr_head_sha", head, head_conflict),
        ("merge_commit_sha", merge, merge_conflict),
        ("release_target_sha", release, release_conflict),
    ):
        if conflict:
            errors.append(f"{label} 冲突：artifact 与传入值不一致，保留 artifact 值 {value or '<empty>'!r}")
        if value and not is_sha(value.lower()):
            errors.append(f"{label} 非法: {value!r}")

    # ---------------- workflow：CI 执行身份 ----------------
    run_id, run_conflict = _first(declared.get("run_id"), ci_run_id)
    attempt, _ = _first(declared.get("attempt"), workflow_attempt)
    job_id, _ = _first(declared.get("job_id"), workflow_job_id)
    if run_conflict:
        errors.append(
            f"workflow.run_id 冲突：artifact={declared.get('run_id')!r} 与传入 {ci_run_id!r} 不一致，"
            "保留 artifact 值"
        )
    if not run_id:
        raise EvidenceError("ci_run_id 不能为空")
    if not attempt:
        errors.append("workflow 缺少 attempt（无法证明是同一次 CI 执行）")
    if not job_id:
        errors.append("workflow 缺少 job_id")

    # ---------------- runtime：环境/镜像/时间必须来自真实事实 ----------------
    environment_value, env_conflict = _first(declared.get("environment"), environment)
    if not environment_value:
        raise EvidenceError("environment 不能为空（必须是真实运行环境，不允许默认 local）")
    if env_conflict:
        errors.append(
            f"environment 冲突：artifact={declared.get('environment')!r} 与传入 {environment!r} "
            "不一致，保留 artifact 值（Builder 不得把 local 改成 ci）"
        )
    if _is_local_environment(environment_value):
        errors.append(
            f"environment={environment_value!r} 为本地/开发环境，不能作为 GA 运行时证据"
        )
    type_value, type_conflict = _first(declared.get("runtime_type"), runtime_type)
    if type_conflict:
        errors.append(
            f"runtime_type 冲突：artifact={declared.get('runtime_type')!r} 与传入 {runtime_type!r} 不一致，"
            "保留 artifact 值"
        )
    if not type_value:
        errors.append("runtime 缺少 runtime_type（无法判定 Runner 形态）")
    elif type_value.lower() not in RUNTIME_TYPES:
        errors.append(f"runtime_type={type_value!r} 未注册（允许 {sorted(RUNTIME_TYPES)}）")
    digest_value, digest_conflict = _first(
        declared.get("driver_image_digest"), driver_image_digest
    )
    if digest_conflict:
        errors.append("driver_image_digest 冲突：artifact 与传入值不一致，保留 artifact 值")
    if type_value.lower() == "container":
        if not is_digest(digest_value):
            errors.append(
                "container Runner 缺少 immutable driver_image_digest（tag 不算 digest）"
            )
    elif digest_value and not is_digest(digest_value):
        errors.append(f"driver_image_digest 非法: {digest_value!r}")

    started_value, started_conflict = _first(declared.get("started_at"), started_at)
    finished_value, finished_conflict = _first(declared.get("finished_at"), finished_at)
    if started_conflict or finished_conflict:
        errors.append("runtime started_at/finished_at 冲突：artifact 与传入值不一致，保留 artifact 值")
    if parse_time(started_value) is None:
        errors.append(f"runtime 缺少合法 started_at: {started_value!r}")
    if parse_time(finished_value) is None:
        errors.append(f"runtime 缺少合法 finished_at: {finished_value!r}")
    computed_runtime = _duration_ms(started_value, finished_value)
    if computed_runtime is not None and computed_runtime < 0:
        computed_runtime = None
    declared_duration = _parse_reported_duration(declared.get("duration_ms"))
    if declared_duration is None:
        runtime_duration = computed_runtime or 0
        duration_source = "computed" if computed_runtime else "missing"
        if not computed_runtime:
            errors.append("runtime 缺少 duration_ms 且无法由 started_at/finished_at 计算")
    else:
        runtime_duration = declared_duration
        duration_source = "artifact"
        if declared_duration <= 0 and computed_runtime:
            errors.append(
                f"runtime.duration_ms={declared_duration} 与起止时间跨度 {computed_runtime}ms 冲突，"
                f"保留原始值 {declared_duration}"
            )
        elif (
            computed_runtime is not None
            and abs(computed_runtime - declared_duration)
            > max(DURATION_TOLERANCE_MS, declared_duration // 10)
        ):
            errors.append(
                f"runtime.duration_ms={declared_duration} 与起止时间跨度 {computed_runtime}ms 冲突，"
                f"保留原始值 {declared_duration}"
            )
    if runtime_duration <= 0:
        errors.append(f"runtime.duration_ms={runtime_duration}，不能作为有效执行记录")

    # ---------------- tests：逐条校验 + 保留逐条事实 ----------------
    seen: set[str] = set()
    records: list[dict] = []
    runtime_type_effective = (type_value or "").lower()
    for index, record in enumerate(tests or []):
        item = validate_record(dict(record), index=index, errors=errors)
        if item["tc_id"] in seen:
            raise EvidenceError(f"重复 TC: {item['tc_id']}")
        seen.add(item["tc_id"])
        if item["status"] == "PASS" and runtime_type_effective == "container":
            if not is_digest(item["driver_image_digest"]):
                errors.append(f"{item['tc_id']}: container Runner 缺少 immutable driver_image_digest")
        records.append(item)
    if require_tcs and len(records) < int(require_tcs):
        raise EvidenceError(f"TC 数量不足：{len(records)} < {require_tcs}")

    # ---------------- artifacts：只汇总，不做存在性判定 ----------------
    artifacts: list[dict[str, Any]] = []
    if source_artifact:
        artifacts.append(
            {
                "tc_id": None,
                "name": _text(source_artifact.get("name")),
                "path": _text(source_artifact.get("path")) or None,
                "sha256": _text(source_artifact.get("sha256")) or None,
                "job_id": source_artifact.get("job_id") or job_id or None,
                "size_bytes": source_artifact.get("size_bytes"),
                "role": "source",
            }
        )
    for item in records:
        for artifact in item["artifacts"]:
            artifacts.append(artifact)
        covered = {(ast["name"], str(ast["path"])) for ast in item["artifacts"]}
        for ref in item["artifact_refs"]:
            entry = _normalize_artifact(
                ref, tc_id=item["tc_id"], default_job_id=item["job_ids"][0] if item["job_ids"] else None
            )
            if (entry["name"], str(entry["path"])) not in covered:
                covered.add((entry["name"], str(entry["path"])))
                artifacts.append(entry)

    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0}
    for item in records:
        counts[item["status"]] += 1
    executed = counts["PASS"] + counts["FAIL"]
    provenance_valid = not errors
    # 去重但保持首次出现顺序，便于人工复核。
    unique_errors = list(dict.fromkeys(errors))
    return {
        "schema_version": "1.1",
        "generated_at": datetime.now(UTC).isoformat(),
        # 兼容旧读取方：commit_sha/ci_run_id/environment 与 source/runtime 保持一致。
        "commit_sha": tested_sha,
        "ci_run_id": run_id,
        "environment": environment_value,
        "source": {
            "tested_commit_sha": tested_sha,
            "tested_commit_sha_origin": "artifact" if declared_sha else "cli",
            "pr_head_sha": head.lower() or None,
            "merge_commit_sha": merge.lower() or None,
            "release_target_sha": release.lower() or None,
        },
        "runtime": {
            "environment": environment_value,
            "runtime_type": type_value or None,
            "driver_image_digest": digest_value or None,
            "started_at": started_value or None,
            "finished_at": finished_value or None,
            "duration_ms": runtime_duration,
            "duration_source": duration_source,
            "computed_duration_ms": computed_runtime,
        },
        "workflow": {
            "run_id": run_id,
            "attempt": int(attempt) if str(attempt).isdigit() else (attempt or None),
            "job_id": job_id or None,
        },
        "artifacts": artifacts,
        "tests": records,
        "summary": {
            **counts,
            "total": len(records),
            "executed": executed,
            "pass_rate_excluding_blocked": round(counts["PASS"] / executed, 4)
            if executed
            else 0.0,
            "provenance_valid": provenance_valid,
            "ga_ready": counts["PASS"] == len(records) and len(records) > 0 and provenance_valid,
        },
        "verification": {
            "provenance_valid": provenance_valid,
            "errors": unique_errors,
        },
    }


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 Runtime E2E 机器结果生成 evidence-index.json")
    parser.add_argument("--input", required=True)
    parser.add_argument("--commit-sha", default="", help="兼容旧参数；与 artifact 不一致会失败")
    parser.add_argument("--tested-commit-sha", default="")
    parser.add_argument("--pr-head-sha", default="")
    parser.add_argument("--merge-commit-sha", default="")
    parser.add_argument("--release-target-sha", default="")
    parser.add_argument("--ci-run", required=True)
    parser.add_argument("--workflow-attempt", default="")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--runtime-type", default="")
    parser.add_argument("--driver-image-digest", default="")
    parser.add_argument("--started-at", default="")
    parser.add_argument("--finished-at", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--require-tcs", type=int, default=10)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    try:
        raw = input_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        tests = payload.get("tests") if isinstance(payload, dict) else payload
        index = build_index(
            tests=list(tests or []),
            commit_sha=args.commit_sha,
            tested_commit_sha=args.tested_commit_sha,
            ci_run_id=args.ci_run,
            environment=args.environment,
            require_tcs=args.require_tcs,
            pr_head_sha=args.pr_head_sha,
            merge_commit_sha=args.merge_commit_sha,
            release_target_sha=args.release_target_sha,
            runtime_type=args.runtime_type,
            driver_image_digest=args.driver_image_digest,
            started_at=args.started_at,
            finished_at=args.finished_at,
            workflow_attempt=args.workflow_attempt,
            workflow_job_id=args.job_id,
            input_payload=payload if isinstance(payload, dict) else None,
            source_artifact={
                "name": input_path.name,
                "path": str(args.input).replace("\\", "/"),
                "sha256": _sha256_bytes(raw),
                "size_bytes": len(raw),
                "job_id": args.job_id or None,
            },
        )
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        print(f"::error::evidence-index: {exc}", file=sys.stderr)
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if not index["verification"]["provenance_valid"]:
        for message in index["verification"]["errors"]:
            print(f"::warning::evidence-index: {message}", file=sys.stderr)
    blocked = index["summary"]["BLOCKED"] + index["summary"]["NOT_RUN"]
    print(json.dumps(index["summary"], ensure_ascii=False))
    if args.fail_on_blocked and blocked:
        print(f"::error::存在 {blocked} 个 BLOCKED/NOT_RUN，不允许宣称 GA", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
