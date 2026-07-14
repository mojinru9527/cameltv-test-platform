"""Regression tests for the Lanhu PostgreSQL reconciliation migration."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260714_lanhu_evidence_pg_reconcile.py"
    )
    spec = importlib.util.spec_from_file_location("lanhu_pg_reconcile", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_repairs_missing_indexes_and_postgres_defaults(monkeypatch):
    migration = _load_migration()
    connection = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    created: list[tuple[str, str, tuple[str, ...]]] = []
    altered: list[tuple[str, str, object]] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(migration, "_index_exists", lambda *_args: False)
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table, columns: created.append((name, table, tuple(columns))),
    )
    monkeypatch.setattr(
        migration.op,
        "alter_column",
        lambda table, column, **kwargs: altered.append(
            (table, column, kwargs["server_default"])
        ),
    )

    migration.upgrade()

    assert {name for name, _table, _columns in created} == {
        "ix_lanhu_evidence_job_project_status",
        "ix_lanhu_evidence_job_project_doc_ver",
        "ix_lanhu_evidence_page_job_order",
        "ix_lanhu_evidence_page_project_page",
        "ix_lanhu_evidence_asset_job_page_type",
    }
    assert {(table, column) for table, column, _default in altered} == {
        ("lanhu_evidence_job", "attempt_no"),
        ("lanhu_evidence_job", "requested_options_json"),
        ("lanhu_evidence_job", "import_result_json"),
        ("lanhu_evidence_page", "capture_truncated"),
        ("lanhu_evidence_page", "review_status"),
        ("lanhu_evidence_page", "reviewer_id"),
        ("lanhu_evidence_page", "review_comment"),
    }


def test_upgrade_is_index_idempotent_and_skips_default_alter_on_sqlite(monkeypatch):
    migration = _load_migration()
    connection = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    created: list[str] = []
    altered: list[str] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(migration, "_index_exists", lambda *_args: True)
    monkeypatch.setattr(
        migration.op, "create_index", lambda name, *_args: created.append(name)
    )
    monkeypatch.setattr(
        migration.op, "alter_column", lambda _table, column, **_kwargs: altered.append(column)
    )

    migration.upgrade()

    assert created == []
    assert altered == []
