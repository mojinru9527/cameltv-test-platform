"""Batch 105 — 组织表迁移与存量项目回填测试。"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import sqlalchemy as sa


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "20260806_batch104_invite_code"


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


def _create_previous_schema(database_path: Path) -> sa.Engine:
    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    metadata = sa.MetaData()
    sa.Table(
        "sys_user",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("nickname", sa.String(), default=""),
        sa.Column("email", sa.String(), default=""),
        sa.Column("status", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    sa.Table(
        "sys_project",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), default=""),
        sa.Column("owner_id", sa.Integer(), default=0),
        sa.Column("status", sa.Integer(), default=1),
        sa.Column("config", sa.String(), default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    sa.Table(
        "sys_project_member",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), default=0),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO sys_user (id, username, password, nickname, email, status) "
                "VALUES (:id, :username, :password, :nickname, :email, 1)"
            ),
            [
                {"id": 1, "username": "alice", "password": "x", "nickname": "Alice", "email": "a@t.local"},
                {"id": 2, "username": "bob", "password": "x", "nickname": "Bob", "email": "b@t.local"},
            ],
        )
        connection.execute(
            sa.text(
                "INSERT INTO sys_project (id, code, name, description, owner_id, status, config) "
                "VALUES (:id, :code, :name, :description, :owner_id, 1, '{}')"
            ),
            [
                {"id": 1, "code": "P1", "name": "Alice 项目", "description": "", "owner_id": 1},
                {"id": 2, "code": "P2", "name": "Bob 项目", "description": "", "owner_id": 2},
                {"id": 3, "code": "P3", "name": "公共项目", "description": "", "owner_id": 0},
            ],
        )
        connection.execute(
            sa.text(
                "INSERT INTO sys_project_member (id, project_id, user_id, role_id) "
                "VALUES (1, 1, 1, 0), (2, 1, 2, 0), (3, 2, 2, 0)"
            )
        )
    return engine


def test_upgrade_backfills_personal_organizations_and_project_ownership(tmp_path: Path) -> None:
    database_path = tmp_path / "batch105-old.db"
    engine = _create_previous_schema(database_path)
    _run_alembic(database_path, "stamp", PREVIOUS_HEAD)

    upgraded = _run_alembic(database_path, "upgrade", "head")
    assert upgraded.returncode == 0

    with engine.connect() as connection:
        orgs = connection.execute(
            sa.text("SELECT id, code, owner_id, type FROM sys_organization ORDER BY owner_id")
        ).all()
        assert [(o.owner_id, o.type) for o in orgs] == [(1, "personal"), (2, "personal")]
        alice_org_id, bob_org_id = orgs[0].id, orgs[1].id

        owners = connection.execute(
            sa.text("SELECT id, organization_id FROM sys_project WHERE id IN (1, 2) ORDER BY id")
        ).all()
        assert owners[0].organization_id == alice_org_id
        assert owners[1].organization_id == bob_org_id
        orphan = connection.execute(
            sa.text("SELECT organization_id FROM sys_project WHERE id = 3")
        ).scalar_one()
        assert orphan is None

        member_rows = connection.execute(
            sa.text(
                "SELECT organization_id, user_id, role_id FROM sys_organization_member "
                "WHERE role_id = 1 ORDER BY user_id"
            )
        ).all()
        assert [(m.organization_id, m.user_id) for m in member_rows] == [
            (alice_org_id, 1),
            (bob_org_id, 2),
        ]

        project_members = connection.execute(
            sa.text("SELECT COUNT(*) FROM sys_project_member")
        ).scalar_one()
        assert project_members == 3  # 原项目成员关系不丢

    # 幂等：重复 upgrade 不报错、不重复建组织
    second = _run_alembic(database_path, "upgrade", "head")
    assert second.returncode == 0
    with engine.connect() as connection:
        count = connection.execute(sa.text("SELECT COUNT(*) FROM sys_organization")).scalar_one()
        assert count == 2


def test_upgrade_creates_organization_tables_when_missing(tmp_path: Path) -> None:
    database_path = tmp_path / "batch105-fresh.db"
    engine = _create_previous_schema(database_path)
    _run_alembic(database_path, "stamp", PREVIOUS_HEAD)
    _run_alembic(database_path, "upgrade", "head")
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                sa.text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        assert "sys_organization" in tables
        assert "sys_organization_member" in tables
