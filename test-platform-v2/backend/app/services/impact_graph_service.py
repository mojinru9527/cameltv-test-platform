"""影响图构建与查询（Batch 260 / B3-1 起）。

设计原则（PRD §1 §3）：**复用既有能力，不新建平行实现**。
本服务只负责把"需求变更 → 模块 → 用例"的关系落成 `ImpactEdge`，
数据来源全部取自既有模块：
  - 需求变更 → 模块：`knowledge/version_differ` + `requirement_module_service`
  - 模块 → 用例：`knowledge/test_case_linker`
覆盖计算、最近执行、缺口分别沿用 `version_coverage_service` / `trace` / `interaction_coverage`，
不在本服务里重算。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.impact_edge import EDGE_KINDS, ImpactEdge


def _validate(source_ref: str, target_ref: str, kind: str) -> None:
    if kind not in EDGE_KINDS:
        raise APIException(
            code=400,
            msg=f"不支持的边类型: {kind!r}（仅支持 {'/'.join(sorted(EDGE_KINDS))}）",
            http_status=400,
        )
    if not (source_ref or "").strip() or not (target_ref or "").strip():
        raise APIException(code=400, msg="边的 source_ref 与 target_ref 都不能为空", http_status=400)


def upsert_edge(
    db: Session,
    *,
    project_id: int,
    source_ref: str,
    target_ref: str,
    kind: str,
    version: str = "",
    confidence: float = 1.0,
) -> tuple[ImpactEdge, bool]:
    """幂等写入一条边。返回 `(edge, created)`。

    幂等的意义：关联构建会被反复执行（每次版本变更/回填），
    如果每次都插新行，图会随执行次数膨胀，覆盖率与影响面都会失真。
    """
    _validate(source_ref, target_ref, kind)
    normalized_version = (version or "").strip()
    existing = db.scalar(
        select(ImpactEdge).where(
            ImpactEdge.project_id == project_id,
            ImpactEdge.source_ref == source_ref,
            ImpactEdge.target_ref == target_ref,
            ImpactEdge.kind == kind,
            ImpactEdge.version == normalized_version,
        )
    )
    if existing is not None:
        existing.confidence = float(confidence)
        db.commit()
        db.refresh(existing)
        return existing, False

    edge = ImpactEdge(
        project_id=project_id,
        source_ref=source_ref,
        target_ref=target_ref,
        kind=kind,
        version=normalized_version,
        confidence=float(confidence),
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge, True


def list_edges(
    db: Session,
    *,
    project_id: int,
    source_ref: str | None = None,
    target_ref: str | None = None,
    kind: str | None = None,
    version: str | None = None,
) -> list[ImpactEdge]:
    where = [ImpactEdge.project_id == project_id]
    if source_ref:
        where.append(ImpactEdge.source_ref == source_ref)
    if target_ref:
        where.append(ImpactEdge.target_ref == target_ref)
    if kind:
        where.append(ImpactEdge.kind == kind)
    if version is not None:
        where.append(ImpactEdge.version == version)
    return list(db.scalars(select(ImpactEdge).where(*where).order_by(ImpactEdge.id.asc())).all())
