"""PostgreSQL server-default contracts for historical migrations."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def _load_migration(filename: str, module_name: str):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / filename
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _EmptyInspector:
    def get_table_names(self) -> list[str]:
        return []

    def get_columns(self, _table_name: str) -> list[dict[str, object]]:
        return []


class _EnvironmentInspector:
    def get_columns(self, table_name: str) -> list[dict[str, object]]:
        assert table_name == "environment"
        return [{"name": "id"}]


def test_created_tables_use_postgresql_compatible_boolean_defaults(monkeypatch) -> None:
    migration = _load_migration(
        "20260722_batch27_m1_knowledge_sphere.py",
        "batch27_knowledge_sphere",
    )
    connection = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    created_columns: list[sa.Column[object]] = []
    added_columns: list[sa.Column[object]] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(migration.sa, "inspect", lambda _connection: _EmptyInspector())
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda _name, *elements, **_kwargs: created_columns.extend(
            element for element in elements if isinstance(element, sa.Column)
        ),
    )
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda _table_name, column: added_columns.append(column),
    )
    monkeypatch.setattr(migration.op, "f", lambda name: name)
    monkeypatch.setattr(migration.op, "create_index", lambda *_args, **_kwargs: None)

    migration.upgrade()

    boolean_columns = [
        column
        for column in created_columns + added_columns
        if isinstance(column.type, sa.Boolean) and column.server_default is not None
    ]
    assert [column.name for column in boolean_columns] == [
        "has_visual_only_content"
    ]
    assert {
        str(
            column.server_default.arg.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).lower()
        for column in boolean_columns
    } <= {"false", "true"}


def test_environment_column_uses_postgresql_compatible_boolean_default(
    monkeypatch,
) -> None:
    migration = _load_migration(
        "af68b09103f3_add_environment_is_production.py",
        "environment_is_production",
    )
    connection = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    added_columns: list[sa.Column[object]] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(
        migration.sa,
        "inspect",
        lambda _connection: _EnvironmentInspector(),
    )
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda _table_name, column: added_columns.append(column),
    )

    migration.upgrade()

    assert [column.name for column in added_columns] == ["is_production"]
    default = added_columns[0].server_default
    assert default is not None
    assert (
        str(
            default.arg.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).lower()
        == "false"
    )
