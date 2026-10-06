"""P1-6/P1-8/P1-9 迁移回归：从基线上 head、单步 downgrade、再 head。

断言三项 DDL 都随迁移出现/回退，且 ORM 声明与迁移索引一致：
- ``ai_jobs.attempt_count``（P1-8 有界回收）
- ``knowledge_trigger_debounce`` 表（P1-9 持久化防抖）
- ``model_usage_ledger(project_id, created_at)`` 复合索引（P1-6 热路径）

全程在独立临时 SQLite 上跑 alembic 子进程，不触碰 dev 库（同
tests/test_batch48_requirement_migration.py 的做法）。
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION = "20260927_ai_guard_and_job_attempts"
COMPOSITE_INDEX = "ix_model_usage_project_created"


def _single_head() -> str:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1, "Alembic 必须保持单头"
    return heads[0]


def _run_alembic(database_path: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "AUTO_CREATE_TABLES": "false",
            "PYTHONPATH": str(BACKEND_ROOT),
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
        timeout=300,
    )


def _schema(database_path: Path) -> dict:
    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        inspector = sa.inspect(engine)
        tables = set(inspector.get_table_names())
        composite = [
            item
            for item in inspector.get_indexes("model_usage_ledger")
            if item["name"] == COMPOSITE_INDEX
        ]
        return {
            "tables": tables,
            "attempt_count": "attempt_count"
            in {c["name"] for c in inspector.get_columns("ai_jobs")},
            "composite_index": [tuple(item["column_names"]) for item in composite],
        }
    finally:
        engine.dispose()


def test_revision_id_fits_widened_version_column() -> None:
    # V3.9 迁移把 alembic_version.version_num 放宽到 VARCHAR(128)，34 字符安全。
    assert len(REVISION) <= 128
    assert _single_head() == REVISION


def test_model_usage_ledger_declares_the_composite_index_in_orm() -> None:
    """create_all（dev/auto_create_tables）与 Alembic 必须声明同一个索引。"""
    from app.modules.aitde.governance.models import ModelUsageLedger

    indexes = {index.name: index for index in ModelUsageLedger.__table__.indexes}
    assert COMPOSITE_INDEX in indexes, sorted(indexes)
    assert [column.name for column in indexes[COMPOSITE_INDEX].columns] == [
        "project_id",
        "created_at",
    ]


def test_migration_adds_and_reverts_all_three_ddl_changes(tmp_path: Path) -> None:
    database_path = tmp_path / "ai-guard-migration.db"

    _run_alembic(database_path, "upgrade", "head")
    upgraded = _schema(database_path)
    assert upgraded["attempt_count"] is True
    assert "knowledge_trigger_debounce" in upgraded["tables"]
    assert upgraded["composite_index"] == [("project_id", "created_at")]

    _run_alembic(database_path, "downgrade", "-1")
    downgraded = _schema(database_path)
    assert downgraded["attempt_count"] is False
    assert "knowledge_trigger_debounce" not in downgraded["tables"]
    assert downgraded["composite_index"] == []

    # 幂等：再次 head 必须能重建（含索引）
    _run_alembic(database_path, "upgrade", "head")
    reapplied = _schema(database_path)
    assert reapplied["attempt_count"] is True
    assert reapplied["composite_index"] == [("project_id", "created_at")]


@pytest.mark.parametrize("index_name", [COMPOSITE_INDEX])
def test_composite_index_name_follows_existing_convention(index_name: str) -> None:
    """沿用生产已有的 ix_model_usage_* 命名（ix_model_usage_project/created）。"""
    assert index_name.startswith("ix_model_usage_")
