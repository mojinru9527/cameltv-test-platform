"""C114-1 — 交互拓扑边 vs 交互用例覆盖缺口提示。

输入：交互拓扑边（from_module → to）与交互用例（tag=interaction:*）。
覆盖判定：边的 to 路径（归一化后）或 to 类型前缀出现在任一用例的 steps/title 文本中，且用例模块与边目标模块一致。
输出：总边数 / 已覆盖 / 覆盖率 / 缺口清单。
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interaction_edge import InteractionEdge
from app.models.test_case import TestCase


def _norm_path(url: str) -> str:
    """Strip domain/query and normalize path. Returns '' for home."""
    path = (url or "").strip()
    if "://" in path:
        path = path.split("://", 1)[1]
    path = path.split("/", 1)[1] if "/" in path else ""
    if "?" in path:
        path = path.split("?", 1)[0]
    if "#" in path:
        path = path.split("#", 1)[0]
    return path.rstrip("/")


def _type_prefix(path: str) -> str:
    """First path segment, e.g. '/football', '/team', '' for home."""
    return "/" + path.split("/", 1)[0] if path else ""


def _case_texts(case: dict) -> list[str]:
    """Collect searchable text from a case (title, module, steps, expected)."""
    texts: list[str] = []
    for key in ("title", "module", "steps", "expected_result"):
        v = case.get(key)
        if isinstance(v, str) and v:
            texts.append(v)
    return texts


# 目标模块 → 页面类型前缀 映射（用于无显式 URL 文本时的语义覆盖判定）
_MODULE_TYPE_HINTS = {
    "赛事详情": "/football",
    "球队详情": "/team",
    "球员详情": "/player",
    "联赛详情": "/league",
    "回放": "/match-replay",
    "世界杯": "/worldcup-2026",
    "资讯": "/q/news",
    "个人中心": "/my",
    "搜索": "/search",
    "首页": "",
}


def _edge_covered(edge: dict, cases: list[dict]) -> bool:
    to_url = str(edge.get("to") or "")
    to_path = _norm_path(to_url)
    to_type = _type_prefix(to_path)
    entry = str(edge.get("entry") or "").strip()
    for case in cases:
        joined = " ".join(_case_texts(case)).lower()
        if to_path and to_path.lower() in joined:
            return True
        if to_type and to_type.lower() in joined:
            return True
        if entry and entry.lower() in joined:
            return True
        module = str(case.get("module") or "").strip()
        if to_type and _MODULE_TYPE_HINTS.get(module) == to_type:
            return True
    return False


def compute_interaction_gaps(edges: list[dict], cases: list[dict]) -> dict:
    covered_edges: list[dict] = []
    gaps: list[dict] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        covered = _edge_covered(edge, cases)
        item = {
            "from_module": str(edge.get("from_module") or ""),
            "entry": str(edge.get("entry") or "")[:120],
            "to": str(edge.get("to") or "")[:200],
        }
        (covered_edges if covered else gaps).append(item)
    total = len(covered_edges) + len(gaps)
    return {
        "total_edges": total,
        "covered_edges": len(covered_edges),
        "gap_edges": len(gaps),
        "coverage_rate": round(len(covered_edges) / total, 4) if total else 0.0,
        "gaps": gaps,
    }


def load_interaction_cases(db: Session, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestCase.tags.like("%interaction%"),
        )
    ).all()
    return [
        {
            "id": r.id,
            "title": r.title or "",
            "module": r.module or "",
            "steps": r.steps or "",
            "expected_result": r.expected_result or "",
        }
        for r in rows
    ]


# ── C120-1 全量拓扑入库 ──

def load_topology_edges(db: Session, project_id: int) -> list[dict]:
    """加载项目内全量交互拓扑边。"""
    rows = db.scalars(
        select(InteractionEdge)
        .where(InteractionEdge.project_id == project_id)
        .order_by(InteractionEdge.id)
    ).all()
    return [
        {
            "from_module": r.from_module,
            "entry": r.entry,
            "to": r.to,
            "evidence": r.evidence,
            "source_batch": r.source_batch,
        }
        for r in rows
    ]


def import_topology_edges(
    db: Session,
    edges: list[dict],
    *,
    project_id: int,
    source_batch: str,
) -> dict:
    """幂等导入拓扑边（按 from_module/entry/to 去重，同键已存在则跳过）。"""
    existing = set()
    for r in db.scalars(select(InteractionEdge).where(InteractionEdge.project_id == project_id)).all():
        existing.add((r.from_module, r.entry, r.to))
    added = 0
    skipped = 0
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        key = (
            str(edge.get("from_module") or ""),
            str(edge.get("entry") or ""),
            str(edge.get("to") or ""),
        )
        if key in existing:
            skipped += 1
            continue
        db.add(InteractionEdge(
            project_id=project_id,
            from_module=key[0],
            entry=key[1],
            to=key[2],
            evidence=str(edge.get("evidence") or ""),
            source_batch=source_batch,
        ))
        existing.add(key)
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped}
