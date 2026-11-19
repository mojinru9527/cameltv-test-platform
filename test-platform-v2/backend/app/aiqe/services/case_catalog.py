"""V16-014-R2：Case Catalog 服务（impact evidence → case/node refs）。"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.case_catalog import CaseCatalogEntry


class CaseCatalogError(ValueError):
    pass


def upsert_entry(
    db: Session,
    *,
    project_id: int,
    case_id: str,
    node_key: str,
    workflow_id: str | None = None,
    route: str = "",
    file_path: str = "",
    symbol: str = "",
    api_operation: str = "",
    tags: Iterable[str] = (),
) -> CaseCatalogEntry:
    key = str(case_id or "").strip()
    if not key:
        raise CaseCatalogError("case_id 不能为空")
    if not str(node_key or "").strip():
        raise CaseCatalogError("node_key 不能为空")
    row = db.scalar(
        select(CaseCatalogEntry).where(
            CaseCatalogEntry.project_id == int(project_id),
            CaseCatalogEntry.case_id == key,
        )
    )
    if row is None:
        row = CaseCatalogEntry(project_id=int(project_id), case_id=key)
        db.add(row)
    row.node_key = str(node_key)[:120]
    row.workflow_id = str(workflow_id) if workflow_id else None
    row.route = str(route or "")[:255]
    row.file_path = str(file_path or "").replace("\\", "/")[:255]
    row.symbol = str(symbol or "")[:160]
    row.api_operation = str(api_operation or "")[:160]
    row.tags_json = sorted({str(tag)[:60] for tag in tags if str(tag).strip()})
    db.flush()
    return row


def list_entries(db: Session, *, project_id: int) -> list[CaseCatalogEntry]:
    return list(
        db.scalars(
            select(CaseCatalogEntry)
            .where(CaseCatalogEntry.project_id == int(project_id))
            .order_by(CaseCatalogEntry.case_id)
        )
    )


def _ref(entry: CaseCatalogEntry) -> str:
    if entry.node_key:
        return f"node:{entry.node_key}"
    return f"case:{entry.case_id}"


def _matches(entry: CaseCatalogEntry, evidence: Mapping[str, Any]) -> bool:
    kind = str(evidence.get("kind") or "")
    detail = str(evidence.get("detail") or "")
    file = str(evidence.get("file") or "").replace("\\", "/")
    if kind == "route" and entry.route and detail:
        return entry.route == detail or entry.route.startswith(detail)
    if kind == "ui_route" and entry.route and detail:
        return entry.route == detail or entry.route.startswith(detail)
    if kind == "symbol" and entry.symbol and detail:
        return entry.symbol == detail
    if kind == "migration" and entry.api_operation and detail:
        return entry.api_operation == detail
    if kind == "dependency" and entry.file_path and file:
        return entry.file_path == file or file.startswith(entry.file_path)
    if file and entry.file_path:
        return entry.file_path == file or file.startswith(entry.file_path.rstrip("/") + "/")
    return False


def match_impact(
    db: Session,
    *,
    project_id: int,
    impact_analysis: Mapping[str, Any],
    allowed_node_keys: Iterable[str] | None = None,
) -> dict[str, Any]:
    """把 A5 证据匹配到 catalog；UNKNOWN 时返回全部节点（更广回归）。"""
    entries = list_entries(db, project_id=project_id)
    allowed = {str(key) for key in allowed_node_keys} if allowed_node_keys is not None else None
    status = str(impact_analysis.get("status") or "")
    matched: list[CaseCatalogEntry] = []
    if status == "UNKNOWN":
        matched = list(entries)
    else:
        evidence = impact_analysis.get("evidence") or []
        for entry in entries:
            if any(
                isinstance(item, Mapping) and _matches(entry, item) for item in evidence
            ):
                matched.append(entry)
    refs = sorted({_ref(entry) for entry in matched})
    node_refs = sorted(
        {
            f"node:{entry.node_key}"
            for entry in matched
            if entry.node_key and (allowed is None or entry.node_key in allowed)
        }
    )
    if status != "UNKNOWN":
        node_refs = [
            ref
            for ref in node_refs
            if allowed is None or ref.removeprefix("node:") in allowed
        ]
    return {
        "status": status or "UNKNOWN",
        "matched_case_ids": sorted({entry.case_id for entry in matched}),
        "scope_refs": node_refs if node_refs else refs,
        "node_refs": node_refs,
        "catalog_size": len(entries),
        "unknown_broadened": status == "UNKNOWN",
    }


def analysis_checksum(analysis: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in analysis.items() if key != "checksum"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_analysis(analysis: Mapping[str, Any]) -> None:
    checksum = str(analysis.get("checksum") or "")
    if not checksum:
        raise CaseCatalogError("impact_analysis 缺 checksum")
    if checksum != analysis_checksum(analysis):
        raise CaseCatalogError("impact_analysis checksum 不匹配")


__all__ = [
    "CaseCatalogEntry",
    "CaseCatalogError",
    "analysis_checksum",
    "list_entries",
    "match_impact",
    "upsert_entry",
    "verify_analysis",
]
