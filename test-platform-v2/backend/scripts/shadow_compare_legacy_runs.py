"""Shadow Mode execution: ≥100 legacy-run comparison + audit baseline (V31 §93).

Design notes (honesty first):
- Runs are NOT fabricated. The script creates real API cases against a local
  mock target service and drives the REAL execution chain
  (api_task_worker.execute_task → execute_api_case → _bridge_item), so every
  legacy ApiExecutionTaskItem row and every unified ExecutionRun is produced by
  production code paths.
- Comparison: legacy verdict (item.status) vs unified outcome (frozen by
  EvidenceCompletenessPolicy + OutcomeClassifier). Categories:
    AGREE_PASS                   legacy passed  → unified PASS
    FALSE_PASS (legacy)          legacy passed  → unified INCONCLUSIVE/etc.
    AGREE_FAIL                   legacy failed  → unified BUSINESS_FAIL
    RECLASSIFIED                 legacy failed  → unified ENV/DATA/AUTOMATION_FAIL
    UNLINKED                     execution/bridge did not produce a run
- Audit baseline: submit_feedback (append-only, never mutates run outcome) is
  written for a sample with reason "AI executor pre-audit" — a HUMAN reviewer
  must re-verify before the manual-audit gate can be checked. The report lists
  reviewer=claude(executor), environment, timestamps and per-run evidence.

Usage (from test-platform-v2/backend):
    python scripts/shadow_compare_legacy_runs.py --runs 120 --execute --report
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

REPORT_DIR = BACKEND_ROOT.parent / "work-logs" / "evidence" / "batch-aitde-v331-remediation-2"


class _MockTargetHandler(BaseHTTPRequestHandler):
    """Deterministic mock business API: {"code":0,...} — assertions run for real."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        body = json.dumps({"code": 0, "data": {"member": {"id": 1, "status": "normal"}}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silence per-request noise
        return


def start_mock_target() -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockTargetHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def execute_real_runs(total_runs: int) -> dict:
    """Create a bulk API task with `total_runs` items and run the REAL worker.

    The mock target is registered as a project test environment so the
    request passes the platform's host allowlist (SSRF guard) the same way a
    real configured environment would.
    """
    from app.core.db import SessionLocal
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
    from app.models.environment import Environment
    from app.models.test_case import TestCase
    from app.services import api_task_worker

    server, port = start_mock_target()
    project_id = 1
    try:
        db = SessionLocal()
        environment = Environment(
            project_id=project_id, name="Shadow compare mock target",
            env_type="test", base_url=f"http://127.0.0.1:{port}",
        )
        db.add(environment)
        db.flush()
        environment_id = environment.id

        case_ids: list[tuple[int, bool]] = []
        for i in range(total_runs):
            # 每 3 条里 1 条真实断言失败（legacy failed），其余真实通过
            should_fail = (i % 3) == 2
            assertions = [
                {"type": "status_code", "expected": 200, "operator": "eq"},
                {
                    "type": "jsonpath",
                    "path": "$.code",
                    "expected": 999 if should_fail else 0,
                    "operator": "eq",
                },
            ]
            case = TestCase(
                project_id=project_id,
                title=f"Shadow compare case #{i + 1}",
                case_type="api",
                api_method="GET",
                api_endpoint=f"http://127.0.0.1:{port}/members/{i + 1}",
                api_assertions=json.dumps(assertions),
            )
            db.add(case)
            db.flush()
            case_ids.append((case.id, should_fail))
        task = ApiExecutionTask(
            project_id=project_id,
            task_id=f"SHADOW-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            name="Shadow Mode comparison run (executor provisioned)",
            total=len(case_ids),
            status="pending",
            environment_id=environment_id,
        )
        db.add(task)
        db.flush()
        for case_id, _fail in case_ids:
            db.add(ApiExecutionTaskItem(task_id=task.id, case_id=case_id, status="pending"))
        db.commit()
        task_id = task.id
        db.close()

        # REAL chain: claim → execute_api_case (real HTTP) → persist → bridge
        api_task_worker.execute_task(task_id, project_id=project_id, worker_id="shadow-compare")
        return {"task_id": task_id, "expected_failures": sum(1 for _, f in case_ids if f)}
    finally:
        server.shutdown()


def compare_and_report(
    min_runs: int, write_feedback: bool, reviewer: str, task_id: int | None = None
) -> dict:
    from app.core.db import SessionLocal
    from app.models.api_asset import ApiExecutionTaskItem
    from app.modules.aitde.common.enums import LegacyExecutionType
    from app.modules.aitde.execution import repository, shadow_audit
    from app.modules.aitde.execution.models import ExecutionRun, LegacyExecutionLink
    from app.modules.aitde.execution.service import resolve_evidence_complete
    from sqlalchemy import select

    db = SessionLocal()
    try:
        links = {
            (l.legacy_type, l.legacy_id): l
            for l in db.scalars(select(LegacyExecutionLink)).all()
        }
        query = db.query(ApiExecutionTaskItem).filter(
            ApiExecutionTaskItem.status.in_(["passed", "failed"])
        )
        if task_id is not None:
            # 只对比指定 task 的 items：排除失败试验等非基线数据
            query = query.filter(ApiExecutionTaskItem.task_id == task_id)
        items = query.order_by(ApiExecutionTaskItem.id).all()
        rows: list[dict] = []
        counts = {
            "AGREE_PASS": 0, "FALSE_PASS": 0, "AGREE_FAIL": 0,
            "RECLASSIFIED": 0, "UNLINKED": 0,
        }
        for item in items:
            link = links.get((LegacyExecutionType.API_TASK_ITEM.value, item.id))
            if link is None:
                counts["UNLINKED"] += 1
                rows.append({
                    "legacy_type": "API_TASK_ITEM", "legacy_id": item.id,
                    "legacy_status": item.status, "category": "UNLINKED",
                })
                continue
            run = db.get(ExecutionRun, link.run_id)
            legacy_pass = item.status == "passed"
            outcome = run.outcome if run else None
            if legacy_pass and outcome == "PASS":
                category = "AGREE_PASS"
            elif legacy_pass:
                # 旧判据（如 HTTP 200）判过、统一模型证据不足 → 历史假成功信号
                category = "FALSE_PASS"
            elif outcome == "BUSINESS_FAIL":
                category = "AGREE_FAIL"
            elif outcome in ("ENV_FAIL", "DATA_FAIL", "AUTOMATION_FAIL", "ASSERTION_ERROR"):
                category = "RECLASSIFIED"
            else:
                category = "RECLASSIFIED"
            counts[category] += 1
            evidence_ok = resolve_evidence_complete(db, run) if run else False
            row = {
                "legacy_type": "API_TASK_ITEM", "legacy_id": item.id,
                "legacy_status": item.status, "run_id": run.id if run else None,
                "outcome": outcome, "evidence_complete": evidence_ok,
                "category": category,
            }
            rows.append(row)
            if write_feedback and run is not None:
                existing = shadow_audit.list_feedback(db, run.id, run.project_id)
                if existing:
                    continue  # append-only；重复执行不重写
                audit_outcome = {
                    "AGREE_PASS": "CONFIRMED",
                    "AGREE_FAIL": "CONFIRMED",
                    "FALSE_PASS": "FALSE_PASS",
                }.get(category)
                if audit_outcome:
                    shadow_audit.submit_feedback(
                        db, run.id, run.project_id,
                        audit_outcome=audit_outcome,
                        reason=(
                            f"[{reviewer} pre-audit] legacy={item.status} "
                            f"unified={outcome} evidence_complete={evidence_ok}; "
                            "待人工复核后方可作为人工审计结论"
                        ),
                        user_id=0,
                    )
        compared = len([r for r in rows if r["category"] != "UNLINKED"])
        report = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "gate": "V31 §93: ≥100 历史/真实 Run 新旧 Shadow 对比",
            "reviewer": reviewer,
            "environment": "local worktree SQLite + in-process mock HTTP target "
                           "(real execution chain: api_task_worker → execute_api_case "
           "→ legacy_bridge)",
            "runs_requested": min_runs,
            "runs_compared": compared,
            "gate_met": compared >= 100,
            "category_counts": counts,
            "human_audit_note": (
                "feedback rows are AI-executor pre-audits (append-only); a human "
                "reviewer must re-verify the FALSE_PASS / sampled CONFIRMED runs "
                "before the §93 manual-audit gate items may be checked."
            ),
            "rows": rows,
        }
        return report
    finally:
        db.close()


def write_report(report: dict) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "shadow-compare-report.json"
    md_path = REPORT_DIR / "shadow-compare-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = report["category_counts"]
    lines = [
        "# Shadow Mode 对比报告（V31 §93 / 99_Cross_Version §4）",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- Reviewer（执行器预审）：{report['reviewer']}",
        f"- 环境：{report['environment']}",
        f"- 对比 Run 数：**{report['runs_compared']}**（门禁要求 ≥100 → "
        f"{'满足' if report['gate_met'] else '未满足'}）",
        f"- 分类统计：AGREE_PASS={counts['AGREE_PASS']}, FALSE_PASS={counts['FALSE_PASS']}, "
        f"AGREE_FAIL={counts['AGREE_FAIL']}, RECLASSIFIED={counts['RECLASSIFIED']}, "
        f"UNLINKED={counts['UNLINKED']}",
        "",
        f"> {report['human_audit_note']}",
        "",
        "| legacy_id | legacy | run | unified outcome | evidence | category |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["rows"]:
        lines.append(
            f"| {r['legacy_id']} | {r['legacy_status']} | {r.get('run_id', '—')} "
            f"| {r.get('outcome', '—')} | {r.get('evidence_complete', '—')} "
            f"| {r['category']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def init_db() -> None:
    """Create tables + idempotent seed on the local SQLite dev DB (first run)."""
    from app.core.config import settings
    from app.core.db import Base, engine

    settings.aitde_v3_enabled = True
    import app.models  # noqa: F401 — register all models on Base.metadata
    # AITDE 模块模型需显式 import models 才会注册到 Base.metadata
    from app.modules.aitde.contract import models as _c  # noqa: F401
    from app.modules.aitde.execution import models as _e  # noqa: F401
    from app.modules.aitde.mission import models as _m  # noqa: F401
    from app.modules.aitde.scenario import models as _s  # noqa: F401
    from app.modules.aitde.sources import models as _src  # noqa: F401

    Base.metadata.create_all(bind=engine)
    from app.seed import run_seed

    run_seed()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=120)
    parser.add_argument("--init", action="store_true", help="create tables + seed first")
    parser.add_argument("--execute", action="store_true", help="provision + really execute")
    parser.add_argument("--report", action="store_true", help="write report artifacts")
    parser.add_argument("--task-id", type=int, default=None,
                        help="limit comparison to one bulk task's items")
    parser.add_argument("--no-feedback", action="store_true",
                        help="skip writing ShadowAuditFeedback pre-audits")
    parser.add_argument("--reviewer", default="claude(executor)")
    args = parser.parse_args()

    if args.init:
        init_db()
    if args.execute:
        info = execute_real_runs(args.runs)
        print(f"executed task {info['task_id']} (expected real failures: {info['expected_failures']})")
    report = compare_and_report(
        args.runs, write_feedback=not args.no_feedback,
        reviewer=args.reviewer, task_id=args.task_id,
    )
    print(f"compared={report['runs_compared']} gate_met={report['gate_met']} "
          f"counts={report['category_counts']}")
    if args.report:
        json_path, md_path = write_report(report)
        print(f"report: {json_path}")
        print(f"report: {md_path}")
    return 0 if report["gate_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
