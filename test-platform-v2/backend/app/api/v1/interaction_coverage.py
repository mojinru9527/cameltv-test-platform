"""C114-1 — 交互拓扑边 vs 用例覆盖缺口提示 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.schemas.interaction_coverage import InteractionGapRequest

router = APIRouter(prefix="/interaction-coverage", tags=["交互覆盖"])


@router.get("/topology", response_model=R[dict], summary="交互拓扑全量边（C120-1）")
def topology_edges(
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """返回项目内全量交互拓扑边（batch-113 3172 边入库后）。"""
    from app.services.interaction_coverage_service import load_topology_edges

    edges = load_topology_edges(db, current.project_id or 0)
    return R.ok({"total": len(edges), "edges": edges})


@router.post("/gaps", response_model=R[dict], summary="交互拓扑覆盖缺口提示（C114-1/C120-1）")
def interaction_coverage_gaps(
    body: InteractionGapRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """对比交互拓扑边与平台交互用例，输出未覆盖边清单与覆盖率。

    请求体不带 edges 时使用库内全量拓扑（C120-1）。
    """
    from app.services.interaction_coverage_service import (
        compute_interaction_gaps,
        load_interaction_cases,
        load_topology_edges,
    )

    pid = current.project_id or 0
    edges = [e.model_dump() for e in body.edges]
    if not edges:
        edges = load_topology_edges(db, pid)
    cases = load_interaction_cases(db, pid)
    result = compute_interaction_gaps(edges, cases)
    return R.ok(result)


@router.post("/import", response_model=R[dict], summary="交互拓扑全量导入（C120-1，幂等）")
def import_topology(
    body: dict,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """批量导入拓扑边（edges: [{from_module, entry, to, evidence}]），按键幂等。"""
    from app.services.interaction_coverage_service import import_topology_edges

    edges = body.get("edges") or []
    source_batch = str(body.get("source_batch") or "batch-113")
    result = import_topology_edges(db, edges, project_id=current.project_id or 0, source_batch=source_batch)
    return R.ok(result)
