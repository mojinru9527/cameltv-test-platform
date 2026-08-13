"""batch-167 Phase 0 — 版本级三类型模块覆盖矩阵。

口径（与用户确认）：
- 模块被「用例覆盖」= 同时存在功能(manual)、接口(api)、UI(ui) 三类用例。
- 模块被「执行覆盖」= API 与 UI 用例均至少执行过一次（pass/fail/skip/block 均为已执行）。
- 分母 = 版本模块树全部 module 节点；模块树为空时回退到项目用例库的 distinct module。
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase

TARGET_RATE = 0.6


class _FallbackModule:
    """模块树为空时的轻量回退模块（不构造 ORM 对象，避免隐式 FK 匹配）。"""

    def __init__(self, id: int | None, name: str) -> None:
        self.id = id
        self.name = name
        self.platform = ""
        self.change_type = "unknown"


def _module_key(name: str) -> str:
    return (name or "").strip().replace(" ", "").lower()


def _match(case_module: str, name: str) -> bool:
    """模块匹配：兼容「用户端/首页」与「首页」两种历史写法。"""
    c = _module_key(case_module)
    m = _module_key(name)
    if not c or not m:
        return False
    return c == m or c.endswith("/" + m) or m.endswith("/" + c) or c in m or m in c


def _canonical_type(raw: str) -> str:
    if raw == "api":
        return "api"
    if raw == "ui":
        return "ui"
    return "manual"


def _load_executed_case_ids(db: Session, project_id: int) -> set[int]:
    sub = (
        select(TestPlanCase.case_id)
        .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
        .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
        .where(TestPlan.project_id == project_id)
        .distinct()
    )
    return {row[0] for row in db.execute(sub).all()}


def compute_bundle_coverage(db: Session, bundle_id: int, project_id: int) -> dict[str, Any]:
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != project_id:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    module_rows = list(db.scalars(
        select(RequirementModule).where(
            RequirementModule.release_bundle_id == bundle_id,
            RequirementModule.node_type == "module",
        ).order_by(RequirementModule.sort_order, RequirementModule.id)
    ).all())

    # 模块树为空时回退到用例库 distinct module（必须在用例统计前完成）
    if not module_rows:
        module_name_rows = db.execute(
            select(TestCase.module).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
                TestCase.module != "",
            ).distinct()
        ).all()
        module_rows = [_FallbackModule(id=None, name=row[0]) for row in module_name_rows]

    cases = list(db.scalars(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
        )
    ).all())
    executed_ids = _load_executed_case_ids(db, project_id)

    # 模块 → 三类型用例统计（priority 取用例库中的最高优先级）
    case_index: dict[tuple[int | None, str], dict[str, int]] = {}
    for case in cases:
        ctype = _canonical_type(case.case_type or "")
        for mod in module_rows:
            mid = getattr(mod, "id", None)
            if (mid is not None and case.requirement_module_id == mid) or _match(case.module or "", mod.name):
                slot = case_index.setdefault((mid, ctype), {"count": 0, "executed": 0, "p0p1": 0})
                slot["count"] += 1
                if case.id in executed_ids:
                    slot["executed"] += 1
                if ctype == "manual" and case.priority in ("P0", "P1"):
                    slot["p0p1"] += 1
                break

    rows: list[dict[str, Any]] = []
    covered = 0
    executed_covered = 0
    p0p1_total = 0
    p0p1_covered = 0
    for mod in module_rows:
        mid = getattr(mod, "id", None)
        entry: dict[str, Any] = {
            "module_id": mid,
            "name": mod.name,
            "platform": mod.platform or "",
            "change_type": mod.change_type or "",
            "functional_count": case_index.get((mid, "manual"), {}).get("count", 0),
            "api_count": case_index.get((mid, "api"), {}).get("count", 0),
            "ui_count": case_index.get((mid, "ui"), {}).get("count", 0),
            "functional_executed": case_index.get((mid, "manual"), {}).get("executed", 0),
            "api_executed": case_index.get((mid, "api"), {}).get("executed", 0),
            "ui_executed": case_index.get((mid, "ui"), {}).get("executed", 0),
            "is_p0p1": bool(case_index.get((mid, "manual"), {}).get("p0p1", 0)),
        }
        gap_types = []
        if entry["functional_count"] == 0:
            gap_types.append("functional")
        if entry["api_count"] == 0:
            gap_types.append("api")
        if entry["ui_count"] == 0:
            gap_types.append("ui")
        entry["gap_types"] = gap_types
        entry["covered"] = not gap_types
        entry["executed_covered"] = entry["api_executed"] > 0 and entry["ui_executed"] > 0
        if entry["covered"]:
            covered += 1
        if entry["executed_covered"]:
            executed_covered += 1
        if entry["is_p0p1"]:
            p0p1_total += 1
            if entry["covered"]:
                p0p1_covered += 1
        rows.append(entry)

    total = len(rows)
    covered_rate = round(covered / total, 4) if total else 0.0
    executed_rate = round(executed_covered / total, 4) if total else 0.0
    return {
        "bundle_id": bundle_id,
        "bundle_name": bundle.name,
        "client_version": bundle.client_version,
        "admin_version": bundle.admin_version,
        "total_modules": total,
        "covered_modules": covered,
        "covered_rate": covered_rate,
        "covered_rate_percent": round(covered_rate * 100, 1),
        "executed_covered_modules": executed_covered,
        "executed_covered_rate": executed_rate,
        "executed_covered_rate_percent": round(executed_rate * 100, 1),
        "p0p1_modules": p0p1_total,
        "p0p1_covered_modules": p0p1_covered,
        "target_rate": TARGET_RATE,
        "target_rate_percent": round(TARGET_RATE * 100, 1),
        "gate_passed": covered_rate >= TARGET_RATE,
        "rows": rows,
    }
