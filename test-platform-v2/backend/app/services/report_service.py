"""Report service — list / get / create (snapshot) / delete."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.defect import Defect
from app.models.quality_gate import QualityGateConfig
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.test_report import TestReport
from app.services.elk_service import build_kibana_link


def _generate_report_id(db: Session, project_id: int) -> str:
    """Generate RP-YYYYMMDD-NNN unique within project."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(TestReport.id)).where(
            TestReport.project_id == project_id,
            TestReport.report_id.like(f"RP-{today}-%"),
        )
    ) or 0
    return f"RP-{today}-{count + 1:03d}"


def _build_content(db: Session, plan_id: int) -> str:
    """Build JSON snapshot of the plan."""
    plan = db.scalar(select(TestPlan).where(TestPlan.id == plan_id))

    plan_info = {}
    if plan:
        plan_info = {
            "id": plan.id,
            "plan_id": plan.plan_id,
            "name": plan.name,
            "description": plan.description,
            "status": plan.status,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
        }

    # plan cases with inline case info
    pcases = db.execute(
        select(TestPlanCase, TestCase)
        .join(TestCase, TestCase.id == TestPlanCase.case_id)
        .where(TestPlanCase.plan_id == plan_id)
        .order_by(TestPlanCase.sort_order)
    ).all()

    # Get latest trace_id per plan case from executions (batch query — was N+1)
    case_trace_map: dict[int, str] = {}
    pcase_ids = [pc.id for pc, _ in pcases]
    if pcase_ids:
        from sqlalchemy import and_, desc

        # Find max executed_at per plan_case_id, then join back to TestExecution
        latest_sub = (
            select(
                TestExecution.plan_case_id,
                func.max(TestExecution.executed_at).label("max_at"),
            )
            .where(TestExecution.plan_case_id.in_(pcase_ids))
            .group_by(TestExecution.plan_case_id)
        ).subquery()

        latest_execs = db.execute(
            select(TestExecution)
            .join(
                latest_sub,
                and_(
                    TestExecution.plan_case_id == latest_sub.c.plan_case_id,
                    TestExecution.executed_at == latest_sub.c.max_at,
                ),
            )
        ).scalars().all()

        for e in latest_execs:
            if e.trace_id:
                case_trace_map[e.plan_case_id] = e.trace_id

    cases = []
    stats = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "block": 0, "pending": 0}
    for pc, tc in pcases:
        trace_id = case_trace_map.get(pc.id, "")
        cases.append({
            "pcase_id": pc.id,
            "case_id": tc.id,
            "case_id_code": tc.case_id,
            "title": tc.title,
            "domain": tc.domain,
            "module": tc.module,
            "priority": tc.priority,
            "case_type": tc.case_type,
            "sort_order": pc.sort_order,
            "last_status": pc.last_status,
            "last_executed_at": pc.last_executed_at.isoformat() if pc.last_executed_at else None,
            "trace_id": trace_id,
            "kibana_link": build_kibana_link(trace_id) if trace_id else "",
        })
        stats["total"] += 1
        key = pc.last_status if pc.last_status in stats else "pending"
        stats[key] = stats.get(key, 0) + 1

    content = {
        "plan_info": plan_info,
        "stats": stats,
        "cases": cases,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(content, ensure_ascii=False)


def list_reports(
    db: Session,
    project_id: int,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """Paginated report list with plan_name."""
    base = (
        select(TestReport, TestPlan.name.label("plan_name"))
        .outerjoin(TestPlan, TestPlan.id == TestReport.plan_id)
        .where(TestReport.project_id == project_id)
    )
    if keyword:
        base = base.where(TestReport.name.contains(keyword))

    total = db.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    ) or 0

    rows = db.execute(
        base.order_by(TestReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for r, plan_name in rows:
        d = {
            "id": r.id,
            "project_id": r.project_id,
            "report_id": r.report_id,
            "name": r.name,
            "description": r.description,
            "plan_id": r.plan_id,
            "template_id": r.template_id,
            "plan_name": plan_name or "",
            "creator_id": r.creator_id,
            "gate_status": r.gate_status,
            "gate_details": _parse_gate_details(r.gate_details),
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        items.append(d)

    return items, total


def get_report(db: Session, report_id: int, project_id: int) -> dict | None:
    row = db.execute(
        select(TestReport, TestPlan.name.label("plan_name"))
        .outerjoin(TestPlan, TestPlan.id == TestReport.plan_id)
        .where(TestReport.id == report_id, TestReport.project_id == project_id)
    ).first()

    if not row:
        return None

    r, plan_name = row
    content = None
    try:
        content = json.loads(r.content)
    except (json.JSONDecodeError, TypeError):
        content = {}

    return {
        "id": r.id,
        "project_id": r.project_id,
        "report_id": r.report_id,
        "name": r.name,
        "description": r.description,
        "plan_id": r.plan_id,
        "template_id": r.template_id,
        "plan_name": plan_name or "",
        "creator_id": r.creator_id,
        "gate_status": r.gate_status,
        "gate_details": _parse_gate_details(r.gate_details),
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "content": content,
    }


def create_report(
    db: Session,
    data,           # ReportCreate
    creator_id: int,
    project_id: int,
) -> dict:
    # Validate plan exists in project
    plan = db.scalar(
        select(TestPlan).where(
            TestPlan.id == data.plan_id,
            TestPlan.project_id == project_id,
        )
    )
    if not plan:
        raise ValueError("计划不存在")

    report_id = _generate_report_id(db, project_id)
    content = _build_content(db, data.plan_id)

    r = TestReport(
        project_id=project_id,
        report_id=report_id,
        name=data.name,
        description=data.description,
        plan_id=data.plan_id,
        template_id=getattr(data, "template_id", None),
        content=content,
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()

    # Compute quality gate with project config
    gate_config = get_quality_gate_config(db, project_id)
    gate = _compute_gate(db, data.plan_id, project_id, content, gate_config)

    # Persist gate result
    r.gate_status = gate["status"]
    r.gate_details = json.dumps(gate["details"], ensure_ascii=False)
    db.flush()

    return {
        "id": r.id,
        "project_id": r.project_id,
        "report_id": r.report_id,
        "name": r.name,
        "description": r.description,
        "plan_id": r.plan_id,
        "template_id": r.template_id,
        "plan_name": plan.name,
        "creator_id": r.creator_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "content": content,
        "gate_status": gate["status"],
        "gate_details": gate["details"],
    }


def _parse_gate_details(gate_details_raw: str | None) -> list:
    """Safely parse gate_details JSON string to list."""
    if not gate_details_raw:
        return []
    try:
        return json.loads(gate_details_raw)
    except (json.JSONDecodeError, TypeError):
        return []


def _compute_gate(db, plan_id: int, project_id: int, content_str: str, config: dict | None = None) -> dict:
    """Compute quality gate for a report. Returns {status, details}.

    Dimensions evaluated (only those with threshold > 0 are enforced):
      1. pass_rate_threshold  — minimum pass rate %
      2. p0_max / p1_max       — max open P0/P1 defects
      3. coverage_threshold    — minimum requirement coverage %
      4. max_failed_cases      — max allowed failed executions
      5. max_blocked_cases     — max allowed blocked executions

    Gate logic: ALL enforced dimensions pass → PASS, ALL fail → FAIL, else WARN.
    """
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except json.JSONDecodeError:
        content = {}

    stats = content.get("stats", {}) if isinstance(content, dict) else {}
    total = stats.get("total", 0)
    pass_count = stats.get("pass", 0)
    fail_count = stats.get("fail", 0)
    block_count = stats.get("block", 0)
    pass_rate = round(pass_count / total * 100, 1) if total else 0

    # Read thresholds from config; 0 means "skip this dimension"
    cfg = config if config and config.get("enabled", True) else {}
    pass_rate_threshold = cfg.get("pass_rate_threshold", 80)
    p0_max = cfg.get("p0_max", 0)
    p1_max = cfg.get("p1_max", 5)
    coverage_threshold = cfg.get("coverage_threshold", 0)
    max_failed_cases = cfg.get("max_failed_cases", 0)
    max_blocked_cases = cfg.get("max_blocked_cases", 0)

    # Check for open defects linked to this plan's cases
    pcases = db.scalars(
        select(TestPlanCase.case_id).where(TestPlanCase.plan_id == plan_id)
    ).all()
    case_ids = set(pcases) if pcases else set()

    p0_defects = 0
    p1_defects = 0
    if case_ids:
        defect_rows = db.execute(
            select(Defect.severity, func.count(Defect.id)).where(
                Defect.project_id == project_id,
                Defect.severity.in_(["P0", "P1"]),
                Defect.status.in_(["open", "confirmed", "fixing"]),
                Defect.case_id.in_(case_ids),
            ).group_by(Defect.severity)
        ).all()
        for sev, cnt in defect_rows:
            if sev == "P0":
                p0_defects = cnt
            elif sev == "P1":
                p1_defects = cnt

    # ── Evaluate each dimension ──
    checks: list[dict] = []

    # 1) Pass rate
    pr_ok = pass_rate >= pass_rate_threshold if pass_rate_threshold > 0 else None
    if pr_ok is not None:
        checks.append({
            "dimension": "pass_rate",
            "value": pass_rate,
            "threshold": pass_rate_threshold,
            "passed": pr_ok,
            "detail": f"通过率 {pass_rate}% {'>=' if pr_ok else '<'} {pass_rate_threshold}%",
        })

    # 2) P0 defects
    if p0_max > 0 or p0_defects > 0:
        checks.append({
            "dimension": "p0_defects",
            "value": p0_defects,
            "threshold": p0_max,
            "passed": p0_defects <= p0_max,
            "detail": f"P0 缺陷 {p0_defects} {'<=' if p0_defects <= p0_max else '>'} {p0_max}",
        })

    # 3) P1 defects
    if p1_max > 0 or p1_defects > 0:
        checks.append({
            "dimension": "p1_defects",
            "value": p1_defects,
            "threshold": p1_max,
            "passed": p1_defects <= p1_max,
            "detail": f"P1 缺陷 {p1_defects} {'<=' if p1_defects <= p1_max else '>'} {p1_max}",
        })

    # 4) Coverage (checks trace data for requirement coverage %)
    coverage_ok: bool | None = None
    if coverage_threshold > 0:
        cov_pct = _compute_coverage(db, plan_id, project_id)
        coverage_ok = cov_pct >= coverage_threshold
        checks.append({
            "dimension": "coverage",
            "value": cov_pct,
            "threshold": coverage_threshold,
            "passed": coverage_ok,
            "detail": f"需求覆盖率 {cov_pct}% {'>=' if coverage_ok else '<'} {coverage_threshold}%",
        })

    # 5) Failed cases cap
    if max_failed_cases > 0:
        fail_ok = fail_count <= max_failed_cases
        checks.append({
            "dimension": "max_failed_cases",
            "value": fail_count,
            "threshold": max_failed_cases,
            "passed": fail_ok,
            "detail": f"失败用例 {fail_count} {'<=' if fail_ok else '>'} {max_failed_cases}",
        })

    # 6) Blocked cases cap
    if max_blocked_cases > 0:
        block_ok = block_count <= max_blocked_cases
        checks.append({
            "dimension": "max_blocked_cases",
            "value": block_count,
            "threshold": max_blocked_cases,
            "passed": block_ok,
            "detail": f"阻塞用例 {block_count} {'<=' if block_ok else '>'} {max_blocked_cases}",
        })

    # ── Aggregate status ──
    enforced = [c for c in checks if c["passed"] is not None]
    if not enforced:
        status = "pass"
    elif all(c["passed"] for c in enforced):
        status = "pass"
    elif not any(c["passed"] for c in enforced):
        status = "fail"
    else:
        status = "warn"

    details = [c["detail"] for c in checks]
    return {"status": status, "details": details, "checks": checks}


def _compute_coverage(db, plan_id: int, project_id: int) -> float:
    """Compute requirement coverage % for a plan: (cases with req links / total)."""
    total_cases = db.scalar(
        select(func.count(TestPlanCase.id)).where(TestPlanCase.plan_id == plan_id)
    ) or 0
    if total_cases == 0:
        return 0.0

    linked = db.scalar(
        select(func.count(TestPlanCase.id))
        .where(TestPlanCase.plan_id == plan_id)
        .where(TestPlanCase.case_id.in_(
            select(TestCase.id).where(TestCase.requirement_doc_id.isnot(None))
        ))
    ) or 0
    return round(linked / total_cases * 100, 1)


# ── Quality Gate Config ───────────────────────────────

def get_quality_gate_config(db: Session, project_id: int) -> dict | None:
    """Get quality gate config for a project. Returns None if not configured."""
    row = db.scalar(
        select(QualityGateConfig).where(QualityGateConfig.project_id == project_id)
    )
    if not row:
        return None
    return {
        "id": row.id,
        "project_id": row.project_id,
        "pass_rate_threshold": row.pass_rate_threshold,
        "p0_max": row.p0_max,
        "p1_max": row.p1_max,
        "coverage_threshold": getattr(row, "coverage_threshold", 0),
        "max_failed_cases": getattr(row, "max_failed_cases", 0),
        "max_blocked_cases": getattr(row, "max_blocked_cases", 0),
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def save_quality_gate_config(db: Session, project_id: int, data: dict) -> dict:
    """Create or update quality gate config for a project. Returns the config dict."""
    row = db.scalar(
        select(QualityGateConfig).where(QualityGateConfig.project_id == project_id)
    )

    _settable = (
        "pass_rate_threshold", "p0_max", "p1_max",
        "coverage_threshold", "max_failed_cases", "max_blocked_cases",
        "enabled",
    )
    if row:
        for k in _settable:
            if k in data and data[k] is not None:
                setattr(row, k, data[k])
    else:
        row = QualityGateConfig(
            project_id=project_id,
            pass_rate_threshold=data.get("pass_rate_threshold", 80),
            p0_max=data.get("p0_max", 0),
            p1_max=data.get("p1_max", 5),
            coverage_threshold=data.get("coverage_threshold", 0),
            max_failed_cases=data.get("max_failed_cases", 0),
            max_blocked_cases=data.get("max_blocked_cases", 0),
            enabled=data.get("enabled", True),
        )
        db.add(row)

    db.flush()
    db.refresh(row)

    return {
        "id": row.id,
        "project_id": row.project_id,
        "pass_rate_threshold": row.pass_rate_threshold,
        "p0_max": row.p0_max,
        "p1_max": row.p1_max,
        "coverage_threshold": getattr(row, "coverage_threshold", 0),
        "max_failed_cases": getattr(row, "max_failed_cases", 0),
        "max_blocked_cases": getattr(row, "max_blocked_cases", 0),
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_report_gate(db: Session, report_id: int, project_id: int) -> dict | None:
    """Get gate evaluation for a report (recomputes from persisted data)."""
    r = db.scalar(
        select(TestReport).where(
            TestReport.id == report_id,
            TestReport.project_id == project_id,
        )
    )
    if not r:
        return None

    # Return persisted gate if available
    details = []
    if r.gate_details:
        try:
            details = json.loads(r.gate_details)
        except json.JSONDecodeError:
            details = []

    return {
        "report_id": r.id,
        "gate_status": r.gate_status or "unknown",
        "gate_details": details,
    }


def get_trends(db: Session, project_id: int) -> dict:
    """Aggregate pass-rate trend and defect convergence across all reports.

    Returns a list of time-sorted data points suitable for line/area charts.
    """
    reports = db.execute(
        select(TestReport).where(TestReport.project_id == project_id)
        .order_by(TestReport.created_at.asc())
    ).scalars().all()

    # Batch load defect data for all reports at once (was N+1 per report)
    from collections import defaultdict

    # 1) Collect plan_ids and timestamps
    report_meta = [(r.id, r.plan_id, r.created_at) for r in reports if r.plan_id]
    all_plan_ids = list({pid for _, pid, _ in report_meta})

    # 2) Batch load all plan_cases for all plan_ids
    plan_case_map: dict[int, set[int]] = {}
    if all_plan_ids:
        pc_rows = db.execute(
            select(TestPlanCase.plan_id, TestPlanCase.case_id)
            .where(TestPlanCase.plan_id.in_(all_plan_ids))
        ).all()
        for pid, cid in pc_rows:
            plan_case_map.setdefault(pid, set()).add(cid)

    # 3) Batch load all relevant defects (all in one query, then group in memory)
    all_case_ids = set()
    for cids in plan_case_map.values():
        all_case_ids.update(cids)

    defects_by_case: dict[int, list[dict]] = defaultdict(list)
    if all_case_ids:
        defect_rows = db.execute(
            select(Defect.case_id, Defect.severity, Defect.status, Defect.created_at, Defect.resolved_at)
            .where(
                Defect.project_id == project_id,
                Defect.case_id.in_(all_case_ids),
            )
        ).all()
        for row in defect_rows:
            defects_by_case[row.case_id].append({
                "severity": row.severity,
                "status": row.status,
                "created_at": row.created_at,
                "resolved_at": row.resolved_at,
            })

    def _compute_open_defects_at(pid: int, at_time) -> dict[str, int]:
        """Count open defects at timestamp using preloaded data."""
        case_ids = plan_case_map.get(pid, set())
        counts: dict[str, int] = {}
        for cid in case_ids:
            for d in defects_by_case.get(cid, []):
                if d["created_at"] and d["created_at"] <= at_time:
                    if d["resolved_at"] is None or d["resolved_at"] > at_time:
                        sev = d["severity"]
                        counts[sev] = counts.get(sev, 0) + 1
        return counts

    points = []
    for r in reports:
        try:
            content = json.loads(r.content) if r.content else {}
        except json.JSONDecodeError:
            content = {}
        stats = content.get("stats", {}) if isinstance(content, dict) else {}
        total = stats.get("total", 0)
        pass_count = stats.get("pass", 0) or stats.get("pass_", 0)
        fail_count = stats.get("fail", 0)
        skip_count = stats.get("skip", 0)
        block_count = stats.get("block", 0)
        pass_rate = round(pass_count / total * 100, 1) if total else 0.0

        # Defect convergence: count open defects using preloaded data
        open_defects = _compute_open_defects_at(r.plan_id, r.created_at) if r.plan_id else {}

        points.append({
            "date": r.created_at.isoformat() if r.created_at else "",
            "report_id": r.id,
            "report_name": r.name,
            "pass_rate": pass_rate,
            "total": total,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "skip_count": skip_count,
            "block_count": block_count,
            "open_p0": open_defects.get("P0", 0),
            "open_p1": open_defects.get("P1", 0),
            "open_p2": open_defects.get("P2", 0),
            "open_total": sum(open_defects.values()),
        })

    # Summary
    rates = [p["pass_rate"] for p in points]
    summary = {
        "total_reports": len(points),
        "avg_pass_rate": round(sum(rates) / len(rates), 1) if rates else 0,
        "best_pass_rate": max(rates) if rates else 0,
        "worst_pass_rate": min(rates) if rates else 0,
        "latest_open_defects": points[-1]["open_total"] if points else 0,
    }

    return {"points": points, "summary": summary}


def _count_open_defects_at(db: Session, project_id: int, plan_id: int, at_time) -> dict[str, int]:
    """Count defects that were still open at the given timestamp, grouped by severity."""
    # Defects linked to this plan's cases that were created before `at_time`
    # and either never resolved, or resolved after `at_time`
    pcases = db.scalars(
        select(TestPlanCase.case_id).where(TestPlanCase.plan_id == plan_id)
    ).all()
    case_ids = set(pcases) if pcases else set()
    if not case_ids:
        return {}

    rows = db.execute(
        select(Defect.severity, func.count(Defect.id))
        .where(
            Defect.project_id == project_id,
            Defect.case_id.in_(case_ids),
            Defect.created_at <= at_time,
            (Defect.resolved_at == None) | (Defect.resolved_at > at_time),
        )
        .group_by(Defect.severity)
    ).all()
    return {sev: cnt for sev, cnt in rows}


def delete_report(db: Session, report_id: int, project_id: int) -> bool:
    r = db.scalar(
        select(TestReport).where(
            TestReport.id == report_id,
            TestReport.project_id == project_id,
        )
    )
    if not r:
        return False
    db.delete(r)
    db.flush()
    return True
