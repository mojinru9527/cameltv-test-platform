"""Backfill canonical links for historical API and UI execution rows.

Default mode is read-only. ``--apply`` calls the existing legacy bridge with
``run_id=None``, which creates a canonical LEGACY_BRIDGE run and writes one
``LegacyExecutionLink``. Legacy execution tables are never modified.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem  # noqa: E402
from app.models.ui_test import UiTestJob, UiTestRun  # noqa: E402
from app.modules.aitde.common.enums import LegacyExecutionType  # noqa: E402
from app.modules.aitde.execution import legacy_bridge  # noqa: E402
from app.modules.aitde.execution.models import LegacyExecutionLink  # noqa: E402

_API_STATUS_TO_STEP = {
    "passed": "SUCCEEDED",
    "failed": "FAILED",
    "skipped": "SKIPPED",
    "pending": "SKIPPED",
}
_UI_STATUS_TO_STEP = {
    "done": "SUCCEEDED",
    "passed": "SUCCEEDED",
    "success": "SUCCEEDED",
    "fail": "FAILED",
    "failed": "FAILED",
    "cancelled": "SKIPPED",
    "pending": "SKIPPED",
    "running": "SKIPPED",
}


@dataclass(frozen=True)
class Candidate:
    item_id: int
    task_id: int
    project_id: int
    environment_id: int
    status: str
    request: Any
    response: Any
    assertions: list[Any]


@dataclass(frozen=True)
class UiCandidate:
    run_id: int
    job_id: int
    project_id: int
    environment_id: int
    status: str
    screenshots: list[str]
    video_url: str | None
    trace_id: str | None
    artifact_dir: str | None
    result_summary: dict[str, Any] | None
    console_text: str | None


def _parse_json(value: str | None) -> Any:
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _parse_assertions(value: str | None) -> list[Any]:
    parsed = _parse_json(value)
    return parsed if isinstance(parsed, list) else []


def _safe_evidence(value: str | None) -> Any:
    """Return JSON-safe migrated evidence without persisting malformed raw text."""
    parsed = _parse_json(value)
    if parsed is None:
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return {"legacy_unparseable": True}


def _api_coverage(db: Session) -> tuple[int, int]:
    total = int(db.scalar(select(func.count(ApiExecutionTaskItem.id))) or 0)
    linked = int(
        db.scalar(
            select(func.count(LegacyExecutionLink.id)).where(
                LegacyExecutionLink.legacy_type == LegacyExecutionType.API_TASK_ITEM.value
            )
        )
        or 0
    )
    return total, linked


def _ui_coverage(db: Session) -> tuple[int, int]:
    total = int(db.scalar(select(func.count(UiTestRun.id))) or 0)
    linked = int(
        db.scalar(
            select(func.count(LegacyExecutionLink.id)).where(
                LegacyExecutionLink.legacy_type == LegacyExecutionType.UI_RUN.value
            )
        )
        or 0
    )
    return total, linked


def load_candidates(
    db: Session,
    *,
    project_id: int | None = None,
    statuses: Iterable[str] | None = None,
    limit: int | None = None,
) -> list[Candidate]:
    stmt = (
        select(ApiExecutionTaskItem, ApiExecutionTask)
        .join(ApiExecutionTask, ApiExecutionTask.id == ApiExecutionTaskItem.task_id)
        .outerjoin(
            LegacyExecutionLink,
            (LegacyExecutionLink.legacy_type == LegacyExecutionType.API_TASK_ITEM.value)
            & (LegacyExecutionLink.legacy_id == ApiExecutionTaskItem.id),
        )
        .where(LegacyExecutionLink.id.is_(None))
        .order_by(ApiExecutionTaskItem.id)
    )
    if project_id is not None:
        stmt = stmt.where(ApiExecutionTask.project_id == project_id)
    status_list = list(statuses or ())
    if status_list:
        stmt = stmt.where(ApiExecutionTaskItem.status.in_(status_list))
    if limit is not None:
        stmt = stmt.limit(limit)

    return [
        Candidate(
            item_id=item.id,
            task_id=item.task_id,
            project_id=task.project_id,
            environment_id=task.environment_id or 0,
            status=item.status,
            request=_safe_evidence(item.request_snapshot),
            response=_safe_evidence(item.response_snapshot),
            assertions=_parse_assertions(item.assertion_results),
        )
        for item, task in db.execute(stmt).all()
    ]


def load_ui_candidates(
    db: Session,
    *,
    project_id: int | None = None,
    statuses: Iterable[str] | None = None,
    limit: int | None = None,
) -> list[UiCandidate]:
    stmt = (
        select(UiTestRun, UiTestJob)
        .join(UiTestJob, UiTestJob.id == UiTestRun.job_id)
        .outerjoin(
            LegacyExecutionLink,
            (LegacyExecutionLink.legacy_type == LegacyExecutionType.UI_RUN.value)
            & (LegacyExecutionLink.legacy_id == UiTestRun.id),
        )
        .where(LegacyExecutionLink.id.is_(None))
        .order_by(UiTestRun.id)
    )
    if project_id is not None:
        stmt = stmt.where(UiTestJob.project_id == project_id)
    status_list = list(statuses or ())
    if status_list:
        stmt = stmt.where(UiTestRun.status.in_(status_list))
    if limit is not None:
        stmt = stmt.limit(limit)

    candidates: list[UiCandidate] = []
    for run, job in db.execute(stmt).all():
        screenshots = _parse_json(run.screenshots)
        result_summary = _parse_json(run.result)
        console_parts = [part for part in (run.stdout, run.stderr) if part]
        candidates.append(
            UiCandidate(
                run_id=run.id,
                job_id=run.job_id,
                project_id=job.project_id,
                environment_id=job.environment_id or 0,
                status=run.status,
                screenshots=screenshots if isinstance(screenshots, list) else [],
                video_url=run.video_url or None,
                trace_id=run.trace_id or None,
                artifact_dir=run.artifact_dir or None,
                result_summary=result_summary if isinstance(result_summary, dict) else None,
                console_text="\n".join(console_parts) if console_parts else None,
            )
        )
    return candidates


def build_plan(
    db: Session,
    *,
    project_id: int | None = None,
    statuses: Iterable[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    total, linked = _api_coverage(db)
    ui_total, ui_linked = _ui_coverage(db)
    candidates = load_candidates(db, project_id=project_id, statuses=statuses, limit=limit)
    ui_candidates = load_ui_candidates(
        db, project_id=project_id, statuses=statuses, limit=limit
    )
    by_status: dict[str, int] = {}
    for candidate in candidates:
        by_status[candidate.status] = by_status.get(candidate.status, 0) + 1
    ui_by_status: dict[str, int] = {}
    for candidate in ui_candidates:
        ui_by_status[candidate.status] = ui_by_status.get(candidate.status, 0) + 1
    return {
        "mode": "dry-run",
        "total_items": total,
        "linked_items": linked,
        "unlinked_items": total - linked,
        "selected_items": len(candidates),
        "selected_by_status": by_status,
        "sample_candidate_ids": [candidate.item_id for candidate in candidates[:20]],
        "ui_total_runs": ui_total,
        "ui_linked_runs": ui_linked,
        "ui_unlinked_runs": ui_total - ui_linked,
        "ui_selected_runs": len(ui_candidates),
        "ui_selected_by_status": ui_by_status,
        "sample_ui_candidate_ids": [candidate.run_id for candidate in ui_candidates[:20]],
    }


def apply_candidates(db: Session, candidates: list[Candidate]) -> dict[str, Any]:
    created = 0
    already_linked = 0
    failures: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            existing = legacy_bridge.find_link(
                db, LegacyExecutionType.API_TASK_ITEM, candidate.item_id
            )
            if existing is not None:
                already_linked += 1
                continue
            legacy_bridge.bridge_api_item(
                db,
                project_id=candidate.project_id,
                run_id=None,
                legacy_id=candidate.item_id,
                request=candidate.request,
                response=candidate.response,
                assertions=candidate.assertions,
                environment_id=candidate.environment_id,
                step_status=_API_STATUS_TO_STEP.get(candidate.status, "SKIPPED"),
            )
            created += 1
        except Exception as exc:  # fail per item, preserve the already committed batch
            db.rollback()
            failures.append(
                {"item_id": candidate.item_id, "error": f"{type(exc).__name__}: {exc}"}
            )
    return {"created": created, "already_linked": already_linked, "failures": failures}


def apply_ui_candidates(db: Session, candidates: list[UiCandidate]) -> dict[str, Any]:
    created = 0
    already_linked = 0
    failures: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            existing = legacy_bridge.find_link(
                db, LegacyExecutionType.UI_RUN, candidate.run_id
            )
            if existing is not None:
                already_linked += 1
                continue
            legacy_bridge.bridge_ui_run(
                db,
                project_id=candidate.project_id,
                run_id=None,
                legacy_id=candidate.run_id,
                screenshots=candidate.screenshots,
                video_url=candidate.video_url,
                trace_id=candidate.trace_id,
                artifact_dir=candidate.artifact_dir,
                result_summary=candidate.result_summary,
                console_text=candidate.console_text,
                environment_id=candidate.environment_id,
                step_status=_UI_STATUS_TO_STEP.get(candidate.status, "SKIPPED"),
            )
            created += 1
        except Exception as exc:  # fail per run, preserve the already committed batch
            db.rollback()
            failures.append(
                {"run_id": candidate.run_id, "error": f"{type(exc).__name__}: {exc}"}
            )
    return {"created": created, "already_linked": already_linked, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write canonical links (default: dry-run)")
    parser.add_argument("--kind", choices=("all", "api", "ui"), default="all")
    parser.add_argument("--project-id", type=int, default=None)
    parser.add_argument("--status", action="append", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    statuses = args.status or None

    with SessionLocal() as db:
        plan = build_plan(
            db,
            project_id=args.project_id,
            statuses=statuses,
            limit=args.limit,
        )
        if not args.apply:
            print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
            return 0

        api_candidates = (
            load_candidates(db, project_id=args.project_id, statuses=statuses, limit=args.limit)
            if args.kind in ("all", "api")
            else []
        )
        ui_candidates = (
            load_ui_candidates(db, project_id=args.project_id, statuses=statuses, limit=args.limit)
            if args.kind in ("all", "ui")
            else []
        )
        api_result = apply_candidates(db, api_candidates)
        ui_result = apply_ui_candidates(db, ui_candidates)
        total, linked = _api_coverage(db)
        ui_total, ui_linked = _ui_coverage(db)
        result = {
            "mode": "apply",
            "kind": args.kind,
            "api_created": api_result["created"],
            "api_already_linked": api_result["already_linked"],
            "api_failures": api_result["failures"],
            "ui_created": ui_result["created"],
            "ui_already_linked": ui_result["already_linked"],
            "ui_failures": ui_result["failures"],
            "selected_items": len(api_candidates),
            "selected_ui_runs": len(ui_candidates),
            "total_items": total,
            "linked_items": linked,
            "unlinked_items": total - linked,
            "ui_total_runs": ui_total,
            "ui_linked_runs": ui_linked,
            "ui_unlinked_runs": ui_total - ui_linked,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if not api_result["failures"] and not ui_result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
