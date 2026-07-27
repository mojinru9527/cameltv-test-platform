"""Template service — CRUD for ReportTemplate.

This is a minimal service for R4 report template feature. Full implementation
includes sections JSON serialization helpers used by the API and smoke tests.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report_template import ReportTemplate, DEFAULT_SECTIONS


# ── JSON helpers ──

def _parse_sections(raw: str) -> list[dict]:
    """Parse sections JSON string → list of dicts. Returns [] on bad input."""
    if not raw or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return []
        return parsed
    except (json.JSONDecodeError, TypeError):
        return []


def _dump_sections(sections: list[dict]) -> str:
    """Serialize sections list → JSON string."""
    return json.dumps(sections, ensure_ascii=False)


def _default_sections_json() -> str:
    return json.dumps(DEFAULT_SECTIONS, ensure_ascii=False)


# ── CRUD ──

def list_templates(db: Session, project_id: int) -> list[dict]:
    rows = db.execute(
        select(ReportTemplate).where(ReportTemplate.project_id == project_id)
        .order_by(ReportTemplate.created_at.desc())
    ).scalars().all()
    return [_template_to_dict(r) for r in rows]


def get_template(db: Session, template_id: int, project_id: int) -> dict | None:
    row = db.scalar(
        select(ReportTemplate).where(
            ReportTemplate.id == template_id,
            ReportTemplate.project_id == project_id,
        )
    )
    return _template_to_dict(row) if row else None


def create_template(db: Session, project_id: int, data: Any) -> dict:
    sections_json = (
        _dump_sections([s.model_dump() for s in data.sections])
        if data.sections else _default_sections_json()
    )
    row = ReportTemplate(
        project_id=project_id,
        name=data.name,
        description=data.description,
        sections=sections_json,
        is_default=data.is_default,
    )
    if data.is_default:
        _clear_other_defaults(db, project_id)
    db.add(row)
    db.flush()
    return _template_to_dict(row)


def update_template(db: Session, template_id: int, project_id: int, data: Any) -> dict | None:
    row = db.scalar(
        select(ReportTemplate).where(
            ReportTemplate.id == template_id,
            ReportTemplate.project_id == project_id,
        )
    )
    if not row:
        return None
    if data.name is not None:
        row.name = data.name
    if data.description is not None:
        row.description = data.description
    if data.sections is not None:
        row.sections = _dump_sections([s.model_dump() for s in data.sections])
    if data.is_default is not None:
        if data.is_default:
            _clear_other_defaults(db, project_id)
        row.is_default = data.is_default
    db.flush()
    return _template_to_dict(row)


def delete_template(db: Session, template_id: int, project_id: int) -> bool:
    row = db.scalar(
        select(ReportTemplate).where(
            ReportTemplate.id == template_id,
            ReportTemplate.project_id == project_id,
        )
    )
    if not row:
        return False
    db.delete(row)
    db.flush()
    return True


def get_default_template(db: Session, project_id: int) -> dict | None:
    row = db.scalar(
        select(ReportTemplate).where(
            ReportTemplate.project_id == project_id,
            ReportTemplate.is_default == True,
        )
    )
    if not row:
        row = db.scalar(
            select(ReportTemplate).where(ReportTemplate.project_id == project_id)
            .order_by(ReportTemplate.created_at.asc())
        )
    return _template_to_dict(row) if row else None


def preview_template(db: Session, template_id: int, project_id: int) -> dict | None:
    """Preview a template with sections expanded."""
    tmpl = get_template(db, template_id, project_id)
    if not tmpl:
        return None
    tmpl["sections_expanded"] = tmpl.get("sections", [])
    return tmpl


# ── Helpers ──

def _clear_other_defaults(db: Session, project_id: int) -> None:
    rows = db.execute(
        select(ReportTemplate).where(
            ReportTemplate.project_id == project_id,
            ReportTemplate.is_default == True,
        )
    ).scalars().all()
    for r in rows:
        r.is_default = False


def _template_to_dict(row: ReportTemplate) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "name": row.name,
        "description": row.description,
        "sections": _parse_sections(row.sections),
        "is_default": row.is_default,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
