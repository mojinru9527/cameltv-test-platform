"""Batch 158 热修：statistics_service._execution_filter 在 PostgreSQL 必须用 IN 包装子查询。

回归：PG 对 WHERE (SELECT ...) 裸标量子查询报
"argument of WHERE must be type boolean, not type integer"（SQLite 宽松不报）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.test_plan import TestPlan as _TestPlan, TestPlanCase as _TestPlanCase
from app.services.statistics_service import _execution_filter


class _FakeDb:
    """捕获编译后的 PG SQL，不真正执行。"""

    def __init__(self) -> None:
        self.sqls: list[str] = []

    def scalar(self, statement) -> int:
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.sqls.append(sql)
        return 0


def _assert_in_wrapped(sqls: list[str]) -> None:
    assert len(sqls) == 3  # total / pass / fail
    for sql in sqls:
        assert "IN (SELECT test_plan_case.id" in sql, sql
        assert "WHERE (SELECT test_plan_case.id" not in sql, sql


def test_default_project_subquery_is_in_wrapped_on_pg() -> None:
    """plan_case_ids_sub=None 时（项目级统计）必须编译为 IN (SELECT ...)。"""
    db = _FakeDb()
    _execution_filter(db, project_id=1)
    _assert_in_wrapped(db.sqls)


def test_explicit_subquery_is_in_wrapped_on_pg() -> None:
    """显式 plan_case_ids_sub（by_type 分支）也必须保持 IN 包装。"""
    sub = (
        select(_TestPlanCase.id)
        .join(_TestPlan, _TestPlan.id == _TestPlanCase.plan_id)
        .where(_TestPlan.project_id == 1)
        .scalar_subquery()
    )
    db = _FakeDb()
    _execution_filter(db, project_id=1, plan_case_ids_sub=sub)
    _assert_in_wrapped(db.sqls)
