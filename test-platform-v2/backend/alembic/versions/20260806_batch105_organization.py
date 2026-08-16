"""batch105_add_organization

Revision ID: 20260806_batch105_organization
Revises: 20260806_batch104_invite_code
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260806_batch105_organization"
down_revision: Union[str, None] = "20260806_batch104_invite_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_member(conn, organization_id: int, user_id: int, role_id: int) -> None:
    exists = conn.execute(
        sa.text(
            "SELECT id FROM sys_organization_member "
            "WHERE organization_id = :oid AND user_id = :uid"
        ),
        {"oid": organization_id, "uid": user_id},
    ).fetchone()
    if not exists:
        conn.execute(
            sa.text(
                "INSERT INTO sys_organization_member "
                "(organization_id, user_id, role_id) VALUES (:oid, :uid, :role)"
            ),
            {"oid": organization_id, "uid": user_id, "role": role_id},
        )


def _backfill_personal_organizations(conn) -> None:
    """为每个存量用户创建个人组织，并将其拥有的项目挂到该组织（幂等）。"""
    owner_ids = [
        row[0]
        for row in conn.execute(
            sa.text("SELECT DISTINCT owner_id FROM sys_project WHERE owner_id > 0")
        ).fetchall()
    ]
    for user_id in owner_ids:
        code = f"personal-{user_id}"
        row = conn.execute(
            sa.text("SELECT id FROM sys_organization WHERE code = :code"),
            {"code": code},
        ).fetchone()
        if row:
            org_id = row[0]
        else:
            # 注：真实表结构中 created_at/updated_at 为非空（后续演进），
            # 回填时必须显式提供时间戳，否则 INSERT 触发 NOT NULL 约束失败。
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat(sep=" ")
            conn.execute(
                sa.text(
                    "INSERT INTO sys_organization "
                    "(code, name, description, type, owner_id, status, created_at, updated_at) "
                    "VALUES (:code, :name, '', 'personal', :owner_id, 1, :now, :now)"
                ),
                {"code": code, "name": "我的组织", "owner_id": user_id, "now": now},
            )
            org_id = conn.execute(
                sa.text("SELECT id FROM sys_organization WHERE code = :code"),
                {"code": code},
            ).scalar_one()
        _ensure_member(conn, org_id, user_id, 1)
        conn.execute(
            sa.text(
                "UPDATE sys_project SET organization_id = :oid "
                "WHERE owner_id = :uid AND organization_id IS NULL"
            ),
            {"oid": org_id, "uid": user_id},
        )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "sys_organization" not in inspector.get_table_names():
        op.create_table(
            "sys_organization",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("description", sa.String(), nullable=False, server_default=""),
            sa.Column("type", sa.String(length=16), nullable=False, server_default="team"),
            sa.Column("owner_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_sys_organization_code", "sys_organization", ["code"], unique=True
        )
        inspector = sa.inspect(conn)

    if "sys_organization_member" not in inspector.get_table_names():
        op.create_table(
            "sys_organization_member",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False, server_default="3"),
            sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        )
        op.create_index(
            "ix_sys_organization_member_organization_id",
            "sys_organization_member",
            ["organization_id"],
        )
        op.create_index(
            "ix_sys_organization_member_user_id",
            "sys_organization_member",
            ["user_id"],
        )

    # 防御式：Batch48 迁移测试等最小旧库可能没有 sys_project，此时无需回填。
    if "sys_project" in inspector.get_table_names():
        project_columns = [c["name"] for c in inspector.get_columns("sys_project")]
        if "organization_id" not in project_columns:
            op.add_column(
                "sys_project",
                sa.Column("organization_id", sa.Integer(), nullable=True),
            )
        _backfill_personal_organizations(conn)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "sys_project" in inspector.get_table_names():
        project_columns = [c["name"] for c in inspector.get_columns("sys_project")]
        if "organization_id" in project_columns:
            op.drop_column("sys_project", "organization_id")
    if "sys_organization_member" in inspector.get_table_names():
        op.drop_table("sys_organization_member")
    if "sys_organization" in inspector.get_table_names():
        op.drop_table("sys_organization")
