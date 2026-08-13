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
from app.models.requirement import RequirementDocument
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


def _bigrams(text: str) -> set[str]:
    return {text[i:i + 2] for i in range(len(text) - 1)}


def _match(case_module: str, name: str) -> bool:
    """模块匹配：兼容「用户端/首页」「广告展示规则 vs 广告前端展示与规则」等历史写法。

    精确相等/包含优先；否则用双字块重叠率（任一方向 >= 0.5）兜底，
    避免 fallback 场景下把同一用例归属到错误模块或全局聚合。
    """
    c = _module_key(case_module)
    m = _module_key(name)
    if not c or not m:
        return False
    if c == m or c.endswith("/" + m) or m.endswith("/" + c) or c in m or m in c:
        return True
    cb = _bigrams(c)
    mb = _bigrams(m)
    overlap = len(cb & mb)
    if overlap == 0:
        return False
    return overlap / len(cb) >= 0.5 or overlap / len(mb) >= 0.5


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
    """计算版本模块的三类型用例覆盖与执行覆盖。

    口径（与用户确认）：
    - 用例覆盖 = 该模块同时存在 manual + api + ui 三类用例。
    - 执行覆盖 = 该模块的 api 与 ui 用例均已至少执行一次。
    - 分母 = 版本模块树全部 module 节点；无模块树时优先取该发布包绑定需求文档
      已导入用例的 distinct module，再回退到项目用例库 distinct module。
    """
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

    fallback_module_names: list[str] = []
    if not module_rows:
        linked_doc_ids = [
            row[0] for row in db.execute(
                select(RequirementDocument.id).where(
                    RequirementDocument.project_id == project_id,
                    RequirementDocument.release_bundle_id == bundle_id,
                )
            ).all()
        ]
        if linked_doc_ids:
            rows = db.execute(
                select(TestCase.module).where(
                    TestCase.project_id == project_id,
                    TestCase.is_deleted.is_(False),
                    TestCase.source_doc_id.in_(linked_doc_ids),
                    TestCase.module != "",
                ).distinct()
            ).all()
            fallback_module_names = [row[0] for row in rows]
        if not fallback_module_names:
            rows = db.execute(
                select(TestCase.module).where(
                    TestCase.project_id == project_id,
                    TestCase.is_deleted.is_(False),
                    TestCase.module != "",
                ).distinct()
            ).all()
            fallback_module_names = [row[0] for row in rows]
        module_rows = [_FallbackModule(id=None, name=name) for name in fallback_module_names]

    # 版本口径：有真实模块树时只统计「挂到该树」或「该发布包绑定需求文档」的用例，
    # 避免其它版本同名/相似模块的用例污染本版本计数。
    linked_doc_ids = [
        row[0] for row in db.execute(
            select(RequirementDocument.id).where(
                RequirementDocument.project_id == project_id,
                RequirementDocument.release_bundle_id == bundle_id,
            )
        ).all()
    ]
    tree_ids = {getattr(m, "id", None) for m in module_rows if getattr(m, "id", None) is not None}
    case_stmt = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.is_deleted.is_(False),
    )
    if tree_ids or linked_doc_ids:
        clauses = []
        if tree_ids:
            clauses.append(TestCase.requirement_module_id.in_(tree_ids))
        if linked_doc_ids:
            clauses.append(TestCase.source_doc_id.in_(linked_doc_ids))
        from sqlalchemy import or_
        case_stmt = case_stmt.where(or_(*clauses))
    cases = list(db.scalars(case_stmt).all())
    executed_ids = _load_executed_case_ids(db, project_id)

    # 模块索引：id 精确匹配 + 规范化名称精确匹配，避免 fallback id=None 时共用聚合键
    id_index: dict[int, int] = {}
    name_index: dict[str, list[int]] = {}
    for idx, mod in enumerate(module_rows):
        mid = getattr(mod, "id", None)
        if mid is not None:
            id_index[mid] = idx
        key = _module_key(mod.name)
        if key:
            name_index.setdefault(key, []).append(idx)

    def _row_key(idx: int, ctype: str) -> tuple[Any, str, str]:
        mod = module_rows[idx]
        return (getattr(mod, "id", None), _module_key(mod.name), ctype)

    case_index: dict[tuple[Any, str, str], dict[str, int]] = {}
    for case in cases:
        ctype = _canonical_type(case.case_type or "")
        target_idx: int | None = None
        if case.requirement_module_id is not None and case.requirement_module_id in id_index:
            target_idx = id_index[case.requirement_module_id]
        else:
            ck = _module_key(case.module or "")
            if ck and ck in name_index:
                target_idx = name_index[ck][0]
            else:
                # 兼容「用户端/首页」与「首页」等历史写法：精确键未命中才做包含式兜底
                for idx, mod in enumerate(module_rows):
                    if _match(case.module or "", mod.name):
                        target_idx = idx
                        break
        if target_idx is None:
            continue
        slot = case_index.setdefault(_row_key(target_idx, ctype), {"count": 0, "executed": 0, "p0p1": 0})
        slot["count"] += 1
        if case.id in executed_ids:
            slot["executed"] += 1
        if ctype == "manual" and case.priority in ("P0", "P1"):
            slot["p0p1"] += 1

    rows: list[dict[str, Any]] = []
    covered = 0
    executed_covered = 0
    p0p1_total = 0
    p0p1_covered = 0
    for idx, mod in enumerate(module_rows):
        mid = getattr(mod, "id", None)
        mkey = _module_key(mod.name)

        def _slot(ctype: str) -> dict[str, int]:
            return case_index.get((mid, mkey, ctype), {})

        entry: dict[str, Any] = {
            "module_id": mid,
            "name": mod.name,
            "platform": mod.platform or "",
            "change_type": mod.change_type or "",
            "functional_count": _slot("manual").get("count", 0),
            "api_count": _slot("api").get("count", 0),
            "ui_count": _slot("ui").get("count", 0),
            "functional_executed": _slot("manual").get("executed", 0),
            "api_executed": _slot("api").get("executed", 0),
            "ui_executed": _slot("ui").get("executed", 0),
            "is_p0p1": bool(_slot("manual").get("p0p1", 0)),
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
