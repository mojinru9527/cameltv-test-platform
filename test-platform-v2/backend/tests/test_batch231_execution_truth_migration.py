from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa


def _load_migration():
    path = (
        Path(__file__).resolve().parent.parent
        / "alembic"
        / "versions"
        / "20260912_b231_execution_truth.py"
    )
    spec = importlib.util.spec_from_file_location("b231_execution_truth", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_repairs_only_latest_zero_execution(monkeypatch):
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    task = sa.Table(
        "version_task",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", sa.String),
        sa.Column("coverage", sa.Text),
    )
    run = sa.Table(
        "version_task_run",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer),
        sa.Column("status", sa.String),
        sa.Column("total", sa.Integer),
        sa.Column("passed", sa.Integer),
        sa.Column("failed", sa.Integer),
        sa.Column("skipped", sa.Integer),
        sa.Column("blocked", sa.Integer),
        sa.Column("failures", sa.Text),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(task.insert(), [
            {"id": 1, "status": "executed", "coverage": "{}"},
            {"id": 2, "status": "executed", "coverage": '{"pass":1}'},
        ])
        connection.execute(run.insert(), [
            {"id": 1, "task_id": 1, "status": "blocked", "total": 0,
             "passed": 0, "failed": 0, "skipped": 0, "blocked": 0, "failures": "[]"},
            {"id": 2, "task_id": 2, "status": "done", "total": 1,
             "passed": 1, "failed": 0, "skipped": 0, "blocked": 0, "failures": "[]"},
        ])
        migration = _load_migration()
        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
        migration.upgrade()

        repaired_run = connection.execute(
            sa.select(run).where(run.c.id == 1)
        ).mappings().one()
        repaired_task = connection.execute(
            sa.select(task).where(task.c.id == 1)
        ).mappings().one()
        healthy_task = connection.execute(
            sa.select(task).where(task.c.id == 2)
        ).mappings().one()

    assert repaired_run["status"] == "blocked"
    assert repaired_run["total"] == repaired_run["blocked"] == 1
    assert "历史运行未执行任何检查" in repaired_run["failures"]
    assert repaired_task["status"] == "blocked"
    assert '"blocked":1' in repaired_task["coverage"]
    assert healthy_task["status"] == "executed"


def test_migration_is_idempotent(monkeypatch):
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "version_task", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", sa.String),
        sa.Column("coverage", sa.Text),
    )
    sa.Table(
        "version_task_run", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer),
        sa.Column("status", sa.String),
        sa.Column("total", sa.Integer),
        sa.Column("passed", sa.Integer),
        sa.Column("failed", sa.Integer),
        sa.Column("skipped", sa.Integer),
        sa.Column("blocked", sa.Integer),
        sa.Column("failures", sa.Text),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        migration = _load_migration()
        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
        migration.upgrade()
        migration.upgrade()

