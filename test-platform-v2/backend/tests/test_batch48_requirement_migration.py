"""Regression coverage for the Batch 48 old-database reconciliation."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "20260726_batch45"
BATCH48_HEAD = "20260727_batch48"


def _alembic_environment(database_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "AUTO_CREATE_TABLES": "false",
            "PYTHONPATH": str(BACKEND_ROOT),
        }
    )
    return environment


def _run_alembic(database_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env=_alembic_environment(database_path),
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    )


def _create_previous_head_schema(database_path: Path) -> sa.Engine:
    """Create only the affected old tables; never use application create_all."""
    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    metadata = sa.MetaData()

    sa.Table(
        "requirement_document",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
    )
    sa.Table(
        "requirement_module",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("release_bundle_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
    )
    sa.Table(
        "module_admin_link",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("client_module_id", sa.Integer(), nullable=False),
        sa.Column("admin_module_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False),
    )
    sa.Table(
        "test_case",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("source_doc_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
    )
    sa.Table(
        "requirement_review",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("case_index", sa.Integer(), nullable=False),
        sa.Column("case_type", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            metadata.tables["requirement_document"].insert(),
            {"id": 1, "project_id": 7, "title": "旧需求"},
        )
        connection.execute(
            metadata.tables["requirement_module"].insert(),
            {
                "id": 1,
                "project_id": 7,
                "release_bundle_id": 11,
                "name": "旧模块",
            },
        )
        connection.execute(
            metadata.tables["module_admin_link"].insert(),
            {
                "id": 1,
                "project_id": 7,
                "client_module_id": 1,
                "admin_module_id": 2,
                "relation_type": "configures",
            },
        )
        connection.execute(
            metadata.tables["module_admin_link"].insert(),
            {
                "id": 2,
                "project_id": 7,
                "client_module_id": 1,
                "admin_module_id": 2,
                "relation_type": "configures",
            },
        )
        connection.execute(
            metadata.tables["test_case"].insert(),
            {
                "id": 1,
                "project_id": 7,
                "source_doc_id": 1,
                "title": "旧用例",
            },
        )
        connection.execute(
            metadata.tables["requirement_review"].insert(),
            {
                "id": 1,
                "requirement_id": 1,
                "case_index": 0,
                "case_type": "func",
                "status": "approved",
            },
        )
        connection.execute(
            metadata.tables["requirement_review"].insert(),
            {
                "id": 2,
                "requirement_id": 1,
                "case_index": 0,
                "case_type": "func",
                "status": "rejected",
            },
        )

    return engine


def _unique_column_sets(inspector: sa.Inspector, table_name: str) -> set[tuple[str, ...]]:
    constraints = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints(table_name)
    }
    indexes = {
        tuple(item["column_names"])
        for item in inspector.get_indexes(table_name)
        if item.get("unique")
    }
    return constraints | indexes


def _assert_duplicate_rejected(
    engine: sa.Engine,
    table_name: str,
    values: dict[str, object],
) -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.table(
                    table_name,
                    *(sa.column(column_name) for column_name in values),
                ).insert(),
                values,
            )
        transaction.rollback()


def test_upgrade_repairs_stamped_old_schema_without_losing_data(tmp_path: Path) -> None:
    database_path = tmp_path / "batch48-old.db"
    engine = _create_previous_head_schema(database_path)
    _run_alembic(database_path, "stamp", PREVIOUS_HEAD)

    _run_alembic(database_path, "upgrade", "head")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE alembic_version SET version_num = :previous_head"
            ),
            {"previous_head": PREVIOUS_HEAD},
        )
    retried_upgrade = _run_alembic(database_path, "upgrade", "head")
    second_upgrade = _run_alembic(database_path, "upgrade", "head")
    current = _run_alembic(database_path, "current")

    assert retried_upgrade.returncode == 0
    assert second_upgrade.returncode == 0
    assert BATCH48_HEAD in current.stdout

    inspector = sa.inspect(engine)
    requirement_columns = {
        item["name"]: item for item in inspector.get_columns("requirement_document")
    }
    assert {
        "release_bundle_id",
        "linked_swagger_id",
        "linked_api_endpoint_ids",
        "extraction_state",
        "extraction_progress",
    } <= requirement_columns.keys()
    assert {
        item["name"] for item in inspector.get_columns("requirement_module")
    } >= {"description", "sort_order"}
    assert "source_case_index" in {
        item["name"] for item in inspector.get_columns("test_case")
    }
    assert "reviewed_at" in {
        item["name"] for item in inspector.get_columns("requirement_review")
    }
    assert "api_token" in inspector.get_table_names()

    assert (
        "project_id",
        "source_doc_id",
        "source_case_index",
    ) in _unique_column_sets(inspector, "test_case")
    assert (
        "requirement_id",
        "case_type",
        "case_index",
    ) in _unique_column_sets(inspector, "requirement_review")
    assert (
        "project_id",
        "client_module_id",
        "admin_module_id",
        "relation_type",
    ) in _unique_column_sets(inspector, "module_admin_link")
    assert "ix_test_case_source_case_index" in {
        item["name"] for item in inspector.get_indexes("test_case")
    }
    assert "ix_requirement_document_release_bundle_id" in {
        item["name"] for item in inspector.get_indexes("requirement_document")
    }
    assert "ix_api_token_project_id" in {
        item["name"] for item in inspector.get_indexes("api_token")
    }

    with engine.begin() as connection:
        document = connection.execute(
            sa.text(
                "SELECT title, linked_api_endpoint_ids, extraction_state, "
                "extraction_progress FROM requirement_document WHERE id = 1"
            )
        ).mappings().one()
        module = connection.execute(
            sa.text(
                "SELECT name, description, sort_order "
                "FROM requirement_module WHERE id = 1"
            )
        ).mappings().one()
        test_case = connection.execute(
            sa.text("SELECT title FROM test_case WHERE id = 1")
        ).scalar_one()
        review_status = connection.execute(
            sa.text(
                "SELECT status FROM requirement_review "
                "WHERE requirement_id = 1 AND case_index = 0"
            )
        ).scalar_one()
        admin_link_ids = connection.execute(
            sa.text(
                "SELECT id FROM module_admin_link "
                "WHERE project_id = 7 AND client_module_id = 1 "
                "AND admin_module_id = 2 AND relation_type = 'configures'"
            )
        ).scalars().all()

        assert dict(document) == {
            "title": "旧需求",
            "linked_api_endpoint_ids": "[]",
            "extraction_state": "{}",
            "extraction_progress": 0.0,
        }
        assert dict(module) == {
            "name": "旧模块",
            "description": "",
            "sort_order": 0,
        }
        assert test_case == "旧用例"
        assert review_status == "rejected"
        assert admin_link_ids == [2]

        connection.execute(
            sa.text(
                "INSERT INTO test_case "
                "(id, project_id, source_doc_id, source_case_index, title) "
                "VALUES (2, 7, 1, 9, '新用例')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO requirement_review "
                "(id, requirement_id, case_index, case_type, status, reviewed_at) "
                "VALUES (3, 1, 1, 'func', 'pending', NULL)"
            )
        )

    _assert_duplicate_rejected(
        engine,
        "test_case",
        {
            "id": 3,
            "project_id": 7,
            "source_doc_id": 1,
            "source_case_index": 9,
            "title": "重复来源用例",
        },
    )
    _assert_duplicate_rejected(
        engine,
        "requirement_review",
        {
            "id": 4,
            "requirement_id": 1,
            "case_index": 1,
            "case_type": "func",
            "status": "pending",
        },
    )
    _assert_duplicate_rejected(
        engine,
        "module_admin_link",
        {
            "id": 3,
            "project_id": 7,
            "client_module_id": 1,
            "admin_module_id": 2,
            "relation_type": "configures",
        },
    )


def test_batch48_is_the_only_head_and_target_models_are_registered() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert heads == [BATCH48_HEAD]
    assert len(BATCH48_HEAD) <= 32

    import app.models  # noqa: F401
    from app.core.db import Base

    assert {
        "requirement_document",
        "requirement_module",
        "module_admin_link",
        "test_case",
        "requirement_review",
        "api_token",
    } <= set(Base.metadata.tables)
    assert {
        "release_bundle_id",
        "linked_swagger_id",
        "linked_api_endpoint_ids",
        "extraction_state",
        "extraction_progress",
    } <= set(Base.metadata.tables["requirement_document"].columns.keys())
    assert {"description", "sort_order"} <= set(
        Base.metadata.tables["requirement_module"].columns.keys()
    )
    assert "source_case_index" in Base.metadata.tables["test_case"].columns
