"""V16-023：从 Runtime E2E 机器结果生成 evidence-index.json。

原则：
- 不得手工填写测试数量；输入必须是测试产出的 JSON；
- PASS 必须具备完整追溯链：commit SHA、CI Run、环境、Run ID、Project、
  WorkflowSnapshot hash、Job IDs、NodeRun IDs、Assertion IDs、Artifact refs；
- BLOCKED/NOT_RUN 不计入通过率，必须给原因；
- 重复 TC、缺失 ID、伪造 ID 一律非零退出。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
TC_RE = re.compile(r"^TC-[A-Z0-9]+-\d{3}$")
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
REQUIRED_PASS_IDS = (
    "run_id",
    "project_id",
    "workflow_snapshot_hash",
    "job_ids",
    "node_run_ids",
    "assertion_ids",
    "artifact_refs",
)


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


def validate_record(record: dict, *, index: int) -> dict:
    tc_id = str(record.get("tc_id") or "").strip()
    if not TC_RE.match(tc_id):
        raise EvidenceError(f"#{index}: tc_id 非法 {tc_id!r}")
    status = str(record.get("status") or "").strip().upper()
    if status not in STATUSES:
        raise EvidenceError(f"{tc_id}: 非法状态 {status!r}")
    out = {
        "tc_id": tc_id,
        "status": status,
        "run_id": record.get("run_id") or None,
        "project_id": int(record["project_id"]) if record.get("project_id") else None,
        "workflow_snapshot_hash": record.get("workflow_snapshot_hash") or "",
        "job_ids": list(record.get("job_ids") or []),
        "node_run_ids": list(record.get("node_run_ids") or []),
        "assertion_ids": list(record.get("assertion_ids") or []),
        "artifact_refs": list(record.get("artifact_refs") or []),
        "driver_image_digest": str(record.get("driver_image_digest") or ""),
        "blocked_reason": str(record.get("blocked_reason") or ""),
        "duration_ms": int(record.get("duration_ms") or 0),
    }
    if status == "PASS":
        missing = [
            key
            for key in REQUIRED_PASS_IDS
            if key == "project_id" and not out["project_id"]
            or key != "project_id" and not _nonempty(out[key])
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
    commit_sha: str,
    ci_run_id: str,
    environment: str,
    require_tcs: int = 0,
) -> dict:
    sha = str(commit_sha or "").strip().lower()
    if not SHA_RE.match(sha):
        raise EvidenceError("commit_sha 必须是完整 40 位 SHA")
    if not str(ci_run_id or "").strip():
        raise EvidenceError("ci_run_id 不能为空")
    if not str(environment or "").strip():
        raise EvidenceError("environment 不能为空")
    seen: set[str] = set()
    records: list[dict] = []
    for index, record in enumerate(tests or []):
        item = validate_record(dict(record), index=index)
        if item["tc_id"] in seen:
            raise EvidenceError(f"重复 TC: {item['tc_id']}")
        seen.add(item["tc_id"])
        records.append(item)
    if require_tcs and len(records) < int(require_tcs):
        raise EvidenceError(f"TC 数量不足：{len(records)} < {require_tcs}")
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0}
    for item in records:
        counts[item["status"]] += 1
    executed = counts["PASS"] + counts["FAIL"]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": sha,
        "ci_run_id": str(ci_run_id),
        "environment": str(environment),
        "tests": records,
        "summary": {
            **counts,
            "total": len(records),
            "executed": executed,
            "pass_rate_excluding_blocked": round(counts["PASS"] / executed, 4)
            if executed
            else 0.0,
            "ga_ready": counts["PASS"] == len(records) and len(records) > 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--ci-run", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--require-tcs", type=int, default=10)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        tests = payload.get("tests") if isinstance(payload, dict) else payload
        index = build_index(
            tests=list(tests or []),
            commit_sha=args.commit_sha,
            ci_run_id=args.ci_run,
            environment=args.environment,
            require_tcs=args.require_tcs,
        )
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        print(f"::error::evidence-index: {exc}", file=sys.stderr)
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    blocked = index["summary"]["BLOCKED"] + index["summary"]["NOT_RUN"]
    print(json.dumps(index["summary"], ensure_ascii=False))
    if args.fail_on_blocked and blocked:
        print(f"::error::存在 {blocked} 个 BLOCKED/NOT_RUN，不允许宣称 GA", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
