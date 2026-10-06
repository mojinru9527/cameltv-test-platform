"""P1-6/P1-8/P1-9: ai_jobs.attempt_count + knowledge_trigger_debounce

Revision ID: 20260927_ai_guard_and_job_attempts
Revises: 20260926_batch260_reuse_suggestion_events
Create Date: 2026-10-06

本次变更涉及三处平台级 AI 治理缺陷，落地时需要的 DDL 有三项：

1. ``ai_jobs.attempt_count``（P1-8）：回收重排必须有界。原实现把心跳丢失的
   running 任务无条件放回 pending，且回收逻辑跑在**每一次**认领上，于是
   「认领 → 超时 → 再认领」会无限循环，每轮白烧一次 LLM。新增计数器后，
   达到 ``AI_JOB_MAX_ATTEMPTS`` 即置为 failed 终态。
2. ``knowledge_trigger_debounce``（P1-9）：知识变更 → Agent 自动触发的防抖状态
   从进程内 dict 搬到数据库。原实现随进程重启清空、多进程各算各的，等于
   「重启即可绕过防抖」重复触发无人值守的 LLM 调用。
3. ``ix_model_usage_project_created``（P1-6）：``model_usage_ledger(project_id,
   created_at)`` 复合索引。配额闸门每次 LLM 调用都要按该组合做两次聚合
   （近 60s 计数、近 24h token 求和），而本表此前只有单列索引、且从 0 行开始
   按每次调用增长，必须给复合索引，否则安全功能自己变成瓶颈。

Revision id 取 ``20260927_...``：与最近 20 个迁移的 ``YYYYMMDD_描述`` 单调前缀
对齐（当前 head 为 ``20260926_batch260_reuse_suggestion_events``）。长度 34 字符
< 128，符合 V3.9 迁移把 ``alembic_version.version_num`` 放宽到 VARCHAR(128) 后的
约束（见 alembic/versions/20260903_aitde_v39_reality_r2_fixture.py 与
tests/test_migration_revision_ids.py）；注意 34 > Alembic 默认的 32，所以它和最近
若干 38~41 字符的 id 一样，依赖那次放宽。

写迁移前已确认：``ai_jobs.attempt_count`` 列、``knowledge_trigger_debounce`` 表与
``ix_model_usage_project_created`` 索引在 alembic/versions/ 中均不存在同名项；
DDL 用独立临时 SQLite 走 from-base 与单步 downgrade 校验（未触碰 dev 库），
回归见 tests/test_ai_guard_migration_indexes.py。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260927_ai_guard_and_job_attempts"
down_revision: Union[str, None] = "20260926_batch260_reuse_suggestion_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    # ── 1. ai_jobs.attempt_count：有界回收的次数计数 ──
    if "ai_jobs" in tables:
        columns = {c["name"] for c in inspector.get_columns("ai_jobs")}
        if "attempt_count" not in columns:
            op.add_column(
                "ai_jobs",
                sa.Column(
                    "attempt_count",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )

    # ── 2. knowledge_trigger_debounce：持久化防抖 ──
    if "knowledge_trigger_debounce" not in tables:
        op.create_table(
            "knowledge_trigger_debounce",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True
            ),
            sa.Column(
                "source_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True
            ),
            sa.Column(
                "agent_type", sa.String(64), nullable=False, server_default=sa.text("''"), index=True
            ),
            sa.Column(
                "triggered_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True
            ),
            sa.UniqueConstraint(
                "project_id",
                "source_id",
                "agent_type",
                name="uq_knowledge_trigger_debounce",
            ),
        )

    # ── 3. model_usage_ledger(project_id, created_at) 复合索引（P1-6 热路径）──
    # 配额闸门每次 LLM 调用都要跑两条聚合：近 60s 行数、近 24h token 之和。
    # 该表原先只有 ix_model_usage_project / ix_model_usage_created 两个单列索引，
    # 24h 求和会退化成「先取该项目全部索引项、再按时间过滤」；本表从 0 行开始、
    # 每次 AI 调用 +1 行且永不清理，在 4C4G 生产机上会成为新的瓶颈。
    if "model_usage_ledger" in tables:
        index_names = {item["name"] for item in inspector.get_indexes("model_usage_ledger")}
        if "ix_model_usage_project_created" not in index_names:
            op.create_index(
                "ix_model_usage_project_created",
                "model_usage_ledger",
                ["project_id", "created_at"],
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "model_usage_ledger" in tables:
        index_names = {item["name"] for item in inspector.get_indexes("model_usage_ledger")}
        if "ix_model_usage_project_created" in index_names:
            op.drop_index("ix_model_usage_project_created", table_name="model_usage_ledger")

    if "knowledge_trigger_debounce" in tables:
        op.drop_table("knowledge_trigger_debounce")

    if "ai_jobs" in tables:
        columns = {c["name"] for c in inspector.get_columns("ai_jobs")}
        if "attempt_count" in columns:
            op.drop_column("ai_jobs", "attempt_count")
