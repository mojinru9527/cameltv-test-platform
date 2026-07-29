"""Contracts for the operator-facing Alembic recovery runbook."""
from __future__ import annotations

from pathlib import Path

from app.models.test_case import TestCase as _CaseModel


RUNBOOK = Path(__file__).parents[1] / "alembic" / "README.md"


def test_runbook_covers_safe_upgrade_and_recovery() -> None:
    content = RUNBOOK.read_text(encoding="utf-8")

    required_commands = (
        "python -m alembic heads",
        "python -m alembic current",
        "python -m alembic upgrade head",
        "python -m alembic downgrade <target_revision>",
    )
    for command in required_commands:
        assert command in content

    required_topics = (
        "备份",
        "恢复",
        "单一 head",
        "staging",
        "行数",
        "应用冒烟",
        "显式修订",
        "真实旧 PostgreSQL",
        "A10",
    )
    for topic in required_topics:
        assert topic in content


def test_runbook_rejects_relative_merge_downgrades_and_empty_db_overclaim() -> None:
    content = RUNBOOK.read_text(encoding="utf-8")

    assert "禁止使用 `python -m alembic downgrade -1`" in content
    assert "临时空数据库不能替代 A10" in content
    assert "生产环境直接执行 `downgrade base`" in content


def test_batch37_requirement_trace_column_remains_in_orm_metadata() -> None:
    column = _CaseModel.__table__.c.source_req_id
    indexed_columns = {
        indexed_column.name
        for index in _CaseModel.__table__.indexes
        for indexed_column in index.columns
    }

    assert column.nullable is False
    assert column.default is not None
    assert "source_req_id" in indexed_columns
