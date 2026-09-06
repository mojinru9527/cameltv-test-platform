from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa


def _load_migration():
    path = (
        Path(__file__).resolve().parent.parent
        / "alembic"
        / "versions"
        / "20260913_b231_traceability_truth.py"
    )
    spec = importlib.util.spec_from_file_location("b231_traceability_truth", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_normalizes_status_and_contract_version_edges(monkeypatch):
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    versions = sa.Table(
        "test_scenario_versions",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("review_status", sa.String),
    )
    edges = sa.Table(
        "lineage_edges",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer),
        sa.Column("from_type", sa.String),
        sa.Column("from_id", sa.Integer),
        sa.Column("to_type", sa.String),
        sa.Column("to_id", sa.Integer),
        sa.Column("edge_type", sa.String),
        sa.UniqueConstraint(
            "project_id",
            "from_type",
            "from_id",
            "to_type",
            "to_id",
            "edge_type",
        ),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            versions.insert(),
            [
                {"id": 1, "review_status": "approve"},
                {"id": 2, "review_status": "request_change"},
            ],
        )
        connection.execute(
            edges.insert(),
            [
                {
                    "id": 1,
                    "project_id": 1,
                    "from_type": "CONTRACT_RULE",
                    "from_id": 5,
                    "to_type": "SCENARIO_VERSION",
                    "to_id": 8,
                    "edge_type": "CONTRACTED_FOR",
                },
                {
                    "id": 2,
                    "project_id": 1,
                    "from_type": "CONTRACT_VERSION",
                    "from_id": 5,
                    "to_type": "SCENARIO_VERSION",
                    "to_id": 8,
                    "edge_type": "CONTRACTED_FOR",
                },
            ],
        )
        migration = _load_migration()
        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
        migration.upgrade()
        migration.upgrade()

        statuses = connection.execute(
            sa.select(versions.c.review_status).order_by(versions.c.id)
        ).scalars().all()
        repaired_edges = connection.execute(sa.select(edges)).mappings().all()

    assert statuses == ["APPROVED", "REQUEST_CHANGE"]
    assert len(repaired_edges) == 1
    assert repaired_edges[0]["from_type"] == "CONTRACT_VERSION"
