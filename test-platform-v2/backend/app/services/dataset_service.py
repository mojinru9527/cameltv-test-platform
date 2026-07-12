"""Dataset service — CRUD, file parsing, parameterized execution support."""
from __future__ import annotations

import csv
import io
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset


# ── CSV / JSON Parsing ───────────────────────────────────

def parse_raw_content(raw_content: str, source_type: str) -> tuple[list[str], list[dict]]:
    """Parse raw content into (column_names, list_of_row_dicts).

    CSV: first line = header, subsequent lines = data rows.
    JSON: must be an array of objects [{"col1": "val1", ...}, ...].

    Returns (columns, rows). Raises ValueError on parse failure.
    """
    if source_type == "csv":
        reader = csv.DictReader(io.StringIO(raw_content))
        if not reader.fieldnames:
            raise ValueError("CSV 没有表头行")
        columns = list(reader.fieldnames)
        rows = [dict(r) for r in reader]
        return columns, rows

    if source_type == "json":
        data = json.loads(raw_content)
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("JSON 必须是非空的对象数组")
        if not all(isinstance(item, dict) for item in data):
            raise ValueError("JSON 数组元素必须是对象")
        # Collect all unique keys as columns (preserving order)
        columns: list[str] = list(dict.fromkeys(k for obj in data for k in obj))
        return columns, data

    raise ValueError(f"不支持的数据源类型: {source_type}")


def preview_dataset(raw_content: str, source_type: str, max_rows: int = 20) -> dict:
    """Parse and return a preview of the first N rows."""
    columns, rows = parse_raw_content(raw_content, source_type)
    return {
        "columns": columns,
        "rows": rows[:max_rows],
        "total_rows": len(rows),
    }


# ── CRUD ─────────────────────────────────────────────────

def list_datasets(
    db: Session,
    *,
    project_id: int = 0,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Paginated list of datasets (light — no raw_content)."""
    stmt = select(Dataset).where(Dataset.project_id == project_id)
    count_stmt = select(func.count(Dataset.id)).where(Dataset.project_id == project_id)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(Dataset.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [_to_light_dict(r) for r in rows], total


def get_dataset(db: Session, dataset_id: int, project_id: int = 0) -> dict | None:
    row = db.scalar(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id)
    )
    return _to_dict(row) if row else None


def create_dataset(db: Session, project_id: int, data: dict) -> dict:
    """Create a dataset and auto-parse columns_meta + row_count."""
    raw_content = data.get("raw_content", "")
    source_type = data.get("source_type", "csv")
    columns, rows = parse_raw_content(raw_content, source_type)

    row = Dataset(
        project_id=project_id,
        name=data["name"],
        description=data.get("description", ""),
        source_type=source_type,
        raw_content=raw_content,
        sql_query="",
        connection_string="",
        row_count=len(rows),
        columns_meta=json.dumps(columns),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def update_dataset(db: Session, dataset_id: int, data: dict) -> dict | None:
    row = db.get(Dataset, dataset_id)
    if not row:
        return None
    # If raw_content changed, re-parse columns_meta and row_count
    if "raw_content" in data and data["raw_content"] is not None:
        raw_content = data["raw_content"]
        source_type = data.get("source_type", row.source_type)
        columns, rows = parse_raw_content(raw_content, source_type)
        row.columns_meta = json.dumps(columns)
        row.row_count = len(rows)
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def delete_dataset(db: Session, dataset_id: int, project_id: int = 0) -> bool:
    row = db.scalar(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id)
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Parameterized Execution Support ──────────────────────

def get_dataset_rows(db: Session, dataset_id: int) -> list[dict]:
    """Return all rows for a dataset as a list of dicts.

    For CSV/JSON: parse raw_content.
    SQL type is deferred for future implementation.
    """
    row = db.get(Dataset, dataset_id)
    if not row:
        raise ValueError(f"Dataset #{dataset_id} not found")
    if row.source_type in ("csv", "json"):
        _, rows = parse_raw_content(row.raw_content, row.source_type)
        return rows
    raise ValueError(f"暂不支持 {row.source_type} 类型的参数化执行")


# ── Helpers ──────────────────────────────────────────────

def _to_dict(r: Dataset) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "name": r.name,
        "description": r.description,
        "source_type": r.source_type,
        "raw_content": r.raw_content,
        "sql_query": r.sql_query,
        "connection_string": r.connection_string,
        "row_count": r.row_count,
        "columns_meta": r.columns_meta,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _to_light_dict(r: Dataset) -> dict:
    """Light version — omit raw_content for list endpoints."""
    d = _to_dict(r)
    d.pop("raw_content", None)
    return d
