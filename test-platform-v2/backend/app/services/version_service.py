"""测试用例版本历史 Service — 自动快照 + 列表查询。"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_case_version import TestCaseVersion


def save_version(db: Session, case_id: int, changed_by: int = 0, changed_fields: str = "") -> dict | None:
    """Save a snapshot of the current TestCase state as a new version.

    Called automatically before update_case() modifies the row.
    """
    case = db.get(TestCase, case_id)
    if not case:
        return None

    # Determine next version number
    latest = db.scalar(
        select(TestCaseVersion.version_number)
        .where(TestCaseVersion.case_id == case_id)
        .order_by(TestCaseVersion.version_number.desc())
    )
    next_ver = (latest + 1) if latest else 1

    snapshot = {
        "case_id": case.case_id,
        "title": case.title,
        "domain": case.domain,
        "module": case.module,
        "case_type": case.case_type,
        "priority": case.priority,
        "status": case.status,
        "preconditions": case.preconditions,
        "steps": case.steps,
        "expected_result": case.expected_result,
        "api_method": case.api_method,
        "api_endpoint": case.api_endpoint,
        "tags": case.tags,
    }

    version = TestCaseVersion(
        case_id=case_id,
        version_number=next_ver,
        snapshot=json.dumps(snapshot, ensure_ascii=False),
        changed_by=changed_by,
        changed_fields=changed_fields,
    )
    db.add(version)
    db.flush()  # persist within current transaction but don't commit yet

    return {
        "id": version.id,
        "case_id": version.case_id,
        "version_number": version.version_number,
        "changed_by": version.changed_by,
        "changed_fields": version.changed_fields,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def list_versions(db: Session, case_id: int) -> list[dict]:
    """Return all version metadata for a test case (without full snapshot for list view)."""
    rows = db.scalars(
        select(TestCaseVersion)
        .where(TestCaseVersion.case_id == case_id)
        .order_by(TestCaseVersion.version_number.desc())
    ).all()

    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "version_number": r.version_number,
            "changed_by": r.changed_by,
            "changed_fields": r.changed_fields.split(",") if r.changed_fields else [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def get_version(db: Session, version_id: int) -> dict | None:
    """Return a single version with full snapshot."""
    r = db.get(TestCaseVersion, version_id)
    if not r:
        return None
    return {
        "id": r.id,
        "case_id": r.case_id,
        "version_number": r.version_number,
        "snapshot": json.loads(r.snapshot) if r.snapshot else {},
        "changed_by": r.changed_by,
        "changed_fields": r.changed_fields.split(",") if r.changed_fields else [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
