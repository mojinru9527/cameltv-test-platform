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
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase

# 需求模块树里"会被当成模块统计覆盖率"的节点类型
MODULE_NODE_TYPES = frozenset({"module"})
# 视为"改动了"的 change_type（来自 knowledge/version_differ：new/modified/deleted）
CHANGED_TYPES = frozenset({"new", "modified"})


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


# ── B3-2 关联构建 ───────────────────────────────────────────────

def _version_label(bundle: ReleaseBundle) -> str:
    return (bundle.client_version or bundle.name or "").strip()


def build_edges(
    db: Session,
    *,
    project_id: int,
    bundle_id: int,
    dry_run: bool = False,
) -> dict:
    """从**既有数据**构建影响图的三类边（Batch 260 / B3-2）。

    复用而非新建解析：
      - 需求变更 → 模块：`RequirementModule.change_type`（由 `knowledge/version_differ` 写入 new/modified/deleted）
      - 模块 → 用例  ：`TestCase.requirement_module_id`（优先）或 `TestCase.module` 名称匹配
      - 模块层级     ：`RequirementModule.parent_module_id` → depends 边

    幂等：同键（project/source/target/kind/version）走 upsert 更新而非重复插入。
    取数全部用批量查询 + 内存映射，**不做循环内查询**（Design §3 P3-2）。
    """
    bundle = db.get(ReleaseBundle, bundle_id)
    if bundle is None or bundle.project_id != project_id:
        raise APIException(code=404, msg="发布包不存在或不属于当前项目", http_status=404)
    version = _version_label(bundle)

    modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.project_id == project_id,
                RequirementModule.release_bundle_id == bundle_id,
            )
        ).all()
    )
    by_id = {m.id: m for m in modules}
    by_name = {m.name: m for m in modules if m.name}

    planned: list[tuple[str, str, str]] = []  # (source_ref, target_ref, kind)
    bundle_ref = f"release_bundle:{bundle_id}"
    for module in modules:
        if module.node_type in MODULE_NODE_TYPES and (module.change_type or "") in CHANGED_TYPES:
            planned.append((bundle_ref, f"module:{module.name}", "changed"))
        if module.parent_module_id and module.parent_module_id in by_id:
            parent = by_id[module.parent_module_id]
            planned.append((f"module:{module.name}", f"module:{parent.name}", "depends"))

    cases = list(
        db.scalars(select(TestCase).where(TestCase.project_id == project_id)).all()
    )
    for case in cases:
        target_name = ""
        if case.requirement_module_id and case.requirement_module_id in by_id:
            target_name = by_id[case.requirement_module_id].name
        elif case.module and case.module in by_name:
            target_name = case.module
        if target_name:
            planned.append((f"case:{case.id}", f"module:{target_name}", "covers"))

    if dry_run:
        return {
            "project_id": project_id,
            "bundle_id": bundle_id,
            "version": version,
            "planned": len(planned),
            "created": 0,
            "updated": 0,
            "dry_run": True,
            "coverage": module_coverage(db, project_id=project_id, bundle_id=bundle_id),
        }

    created = updated = 0
    for source_ref, target_ref, kind in planned:
        _edge, was_created = upsert_edge(
            db,
            project_id=project_id,
            source_ref=source_ref,
            target_ref=target_ref,
            kind=kind,
            version=version,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "project_id": project_id,
        "bundle_id": bundle_id,
        "version": version,
        "planned": len(planned),
        "created": created,
        "updated": updated,
        "dry_run": False,
        "coverage": module_coverage(db, project_id=project_id, bundle_id=bundle_id),
    }


def module_coverage(db: Session, *, project_id: int, bundle_id: int) -> dict:
    """模块级关联覆盖率：该发布包下的模块里，有多少至少被一条用例覆盖。

    B3-2 的 DoD（体育试点模块关联覆盖率 ≥90%）由本函数产出数字。
    """
    modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.project_id == project_id,
                RequirementModule.release_bundle_id == bundle_id,
                RequirementModule.node_type.in_(sorted(MODULE_NODE_TYPES)),
            )
        ).all()
    )
    names = [m.name for m in modules if m.name]
    covered_targets = {
        edge.target_ref
        for edge in db.scalars(
            select(ImpactEdge).where(
                ImpactEdge.project_id == project_id,
                ImpactEdge.kind == "covers",
            )
        ).all()
    }
    covered = [name for name in names if f"module:{name}" in covered_targets]
    uncovered = [name for name in names if f"module:{name}" not in covered_targets]
    total = len(names)
    return {
        "total_modules": total,
        "covered_modules": len(covered),
        "uncovered_modules": uncovered,
        "coverage_rate": round(len(covered) / total, 4) if total else 0.0,
    }
