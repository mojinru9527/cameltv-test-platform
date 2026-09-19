"""「改了 X 要跑哪些」查询（Batch 260 / B3-3）。

09 方案 §2.4 的唯一知识问题：
    改了哪些需求/功能模块 → 要跑哪些用例 → 上次跑得怎么样？

**复用而非重建**（PRD §1 §3）：本服务只把四段拼成一次查询——
  - 关联用例：`ImpactEdge` 的 `covers` 边（B3-2 已构建）
  - 最近一次执行结果：`TestPlanCase.last_status/last_executed_at`（既有去规范化字段，无需 join 执行明细）
  - 未覆盖缺口：同一批边数据里没有 `covers` 目标的模块
  - 受影响模块：命中的模块 + 通过 `depends` 边指向它们的上游模块
覆盖计算沿用既有口径，**不在这里重算**（`version_coverage_service` 仍是唯一实现）。

性能约束（Design §3 P3-2）：**查询条数不随模块数增长**——所有取数都是批量 select + 内存映射，
没有任何"循环里发查询"。`tests/test_batch260_impact_query.py` 用 SQL 计数断言守着这一点。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.impact_edge import ImpactEdge
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.models.test_plan import TestPlan, TestPlanCase

# 用例类型归一：库里是 api/manual/ui，对外按"功能/接口/UI"三组给
CASE_GROUP_BY_TYPE = {"api": "api", "ui": "ui", "manual": "functional"}


def _module_refs(matched: list[RequirementModule], depended_by: set[str]) -> list[str]:
    names = {m.name for m in matched if m.name}
    return sorted(names | depended_by)


def what_to_run(
    db: Session,
    *,
    project_id: int,
    module: str,
    version: str = "",
) -> dict:
    """一次查询回答「改了 X 要跑哪些」。"""
    needle = (module or "").strip()
    if not needle:
        raise APIException(code=400, msg="请提供模块名（module）", http_status=400)
    version_label = (version or "").strip()

    # ① 命中的模块（名称包含匹配；限定版本时只取该发布包下的模块）
    module_query = select(RequirementModule).where(
        RequirementModule.project_id == project_id,
        RequirementModule.node_type == "module",
    )
    if version_label:
        bundle_ids = list(
            db.scalars(
                select(ReleaseBundle.id).where(
                    ReleaseBundle.project_id == project_id,
                    ReleaseBundle.client_version == version_label,
                )
            ).all()
        )
        if not bundle_ids:
            return _empty_result(project_id, needle, version_label, reason="版本不存在或没有模块")
        module_query = module_query.where(RequirementModule.release_bundle_id.in_(bundle_ids))
    modules = list(db.scalars(module_query).all())
    matched = [m for m in modules if m.name and needle in m.name]
    matched_names = {m.name for m in matched}

    # ② 受影响模块 = 命中模块 + 依赖它们的上游（depends 边 source→target，target 命中即 source 受影响）
    edge_query = select(ImpactEdge).where(ImpactEdge.project_id == project_id)
    if version_label:
        edge_query = edge_query.where(ImpactEdge.version.in_([version_label, ""]))
    edges = list(db.scalars(edge_query).all())
    affected_names = set(matched_names)
    for edge in edges:
        if edge.kind == "depends" and edge.target_ref in {f"module:{n}" for n in matched_names}:
            affected_names.add(edge.source_ref.removeprefix("module:"))

    # ③ 关联用例：covers 边指向受影响模块（或直接用模块名字段兜底）
    case_ids = {
        int(edge.source_ref.removeprefix("case:"))
        for edge in edges
        if edge.kind == "covers"
        and edge.target_ref in {f"module:{n}" for n in affected_names}
        and edge.source_ref.startswith("case:")
        and edge.source_ref.removeprefix("case:").isdigit()
    }
    case_query = select(TestCase).where(TestCase.project_id == project_id)
    if case_ids:
        case_query = case_query.where(TestCase.id.in_(sorted(case_ids)))
    else:
        case_query = case_query.where(TestCase.module.in_(sorted(affected_names)))
    cases = list(db.scalars(case_query).all())

    # ④ 最近一次执行结果（批量：一次取全部相关 plan_case，不做 per-case 查询）
    grouped: dict[str, list[dict]] = {"functional": [], "api": [], "ui": []}
    last_runs: list[dict] = []
    if cases:
        case_id_list = [c.id for c in cases]
        plan_cases = list(
            db.scalars(
                select(TestPlanCase)
                .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
                .where(
                    TestPlan.project_id == project_id,
                    TestPlanCase.case_id.in_(case_id_list),
                )
            ).all()
        )
        latest_by_case: dict[int, TestPlanCase] = {}
        for plan_case in plan_cases:
            # 显式标注：mypy 需要它才能正确处理 `.get()` 的 Optional 返回，
            # 否则会报 assignment: TestPlanCase | None 赋给 TestPlanCase。
            current: TestPlanCase | None = latest_by_case.get(plan_case.case_id)
            if current is None or (plan_case.last_executed_at or plan_case.created_at) > (
                current.last_executed_at or current.created_at
            ):
                latest_by_case[plan_case.case_id] = plan_case
        for case in cases:
            group = CASE_GROUP_BY_TYPE.get((case.case_type or "manual").lower(), "functional")
            item = {
                "case_id": case.id,
                "title": case.title,
                "module": case.module,
                "case_type": case.case_type,
                "ref": f"case:{case.id}",
            }
            grouped[group].append(item)
            # 不要复用上面的循环变量名 `plan_case`：它已被绑定为 TestPlanCase，
            # 再赋 `dict.get()` 的 Optional 返回值会触发 mypy assignment 错误。
            latest_plan_case: TestPlanCase | None = latest_by_case.get(case.id)
            if latest_plan_case is not None:
                last_runs.append(
                    {
                        "case_id": case.id,
                        "plan_id": latest_plan_case.plan_id,
                        "status": latest_plan_case.last_status,
                        "executed_at": latest_plan_case.last_executed_at.isoformat()
                        if latest_plan_case.last_executed_at
                        else None,
                        "ref": f"plan:{latest_plan_case.plan_id}",
                    }
                )

    # ⑤ 缺口：受影响模块里没有任何 covers 边的
    covered_names = {
        edge.target_ref.removeprefix("module:")
        for edge in edges
        if edge.kind == "covers" and edge.target_ref.startswith("module:")
    }
    gaps = sorted(name for name in affected_names if name not in covered_names)

    return {
        "project_id": project_id,
        "query": {"module": needle, "version": version_label},
        "affected_modules": sorted(affected_names),
        "cases": grouped,
        "counts": {
            "affected_modules": len(affected_names),
            "functional": len(grouped["functional"]),
            "api": len(grouped["api"]),
            "ui": len(grouped["ui"]),
            "cases_total": len(cases),
            "gaps": len(gaps),
        },
        "last_runs": last_runs,
        "gaps": gaps,
        "refs": {
            "modules": [f"module:{name}" for name in sorted(affected_names)],
            "cases": [f"case:{case.id}" for case in cases],
        },
    }


def _empty_result(project_id: int, module: str, version: str, *, reason: str) -> dict:
    return {
        "project_id": project_id,
        "query": {"module": module, "version": version},
        "affected_modules": [],
        "cases": {"functional": [], "api": [], "ui": []},
        "counts": {
            "affected_modules": 0,
            "functional": 0,
            "api": 0,
            "ui": 0,
            "cases_total": 0,
            "gaps": 0,
        },
        "last_runs": [],
        "gaps": [],
        "refs": {"modules": [], "cases": []},
        "reason": reason,
    }
