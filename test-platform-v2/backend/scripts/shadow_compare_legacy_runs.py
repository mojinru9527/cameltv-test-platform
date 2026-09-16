"""Read-only Shadow Mode comparison for historical legacy runs (V31 §93).

The legacy executor has been deleted. This script only reads existing
ApiExecutionTaskItem rows and LegacyExecutionLink mappings to compare the
historical legacy verdict with the canonical ExecutionRun outcome.
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
    python scripts/shadow_compare_legacy_runs.py --runs 120 --report
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

REPORT_DIR = BACKEND_ROOT.parent / "work-logs" / "evidence" / "batch-aitde-v331-remediation-2"


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
            "environment": "historical read-only comparison (canonical run + legacy link)",
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
    parser.add_argument("--report", action="store_true", help="write report artifacts")
    parser.add_argument("--task-id", type=int, default=None,
                        help="limit comparison to one bulk task's items")
    parser.add_argument("--no-feedback", action="store_true",
                        help="skip writing ShadowAuditFeedback pre-audits")
    parser.add_argument("--reviewer", default="claude(executor)")
    args = parser.parse_args()

    if args.init:
        init_db()
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
