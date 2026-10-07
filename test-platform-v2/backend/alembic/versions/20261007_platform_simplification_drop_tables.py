"""平台简化批次：删除已下线模块的全部数据表 + projects.organization_id

Revision ID: 20261007_platform_simplification_drop_tables
Revises: 20260927_ai_guard_and_job_attempts
Create Date: 2026-10-07

删除域：AITDE（missions/契约/场景/数据/执行治理/生产证据/智能回归/愈合/Flaky）、
DSH 任务、报告中心/模板、测试数据集、通知、集成/同步、组织、旧版本测试任务
（version_mission）、AI 本地管线（ai_jobs/ai_results）、知识图谱 UI 域
（agent_run/ai_artifact/迭代/快照/防抖/实体图谱快照）、LLM-Wiki 差异/审查/外部连接。

保留：执行事实表（execution_runs/scenario/legacy_object_mappings/evidence 等，
随 execution_runtime 模块）、campaign 表、项目知识（knowledge_source/chunk/vector/
entity/relation）、wiki 核心页表、AI 配置/额度台账（ai_provider/model_usage_ledger）。

幂等约定（对齐 b191 惯例）：每张表 DROP 前用 inspector 检查存在性；
stamp 回退后重跑 upgrade 可自愈。downgrade 无法恢复已销毁数据，保持 no-op。

⚠ 生产执行前必须备份（docs/ops/restore-drill.md 链路已验证：pg_dump → pg_restore → 抽查）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20261007_platform_simplification_drop_tables'
down_revision: Union[str, None] = '20260927_ai_guard_and_job_attempts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 已删除模块的表（表名来自被删模型文件的 __tablename__，按字母序）
_DROP_TABLES: tuple[str, ...] = (
    "agent_queue_item", "agent_run", "agent_work_log", "ai_artifact", "ai_jobs",
    "ai_operation_records", "ai_results", "ai_suggestions", "ambiguities",
    "approval_requests", "browser_observation_events", "browser_sessions",
    "build_observations", "campaign_scenarios", "change_items", "change_proposals",
    "change_sets", "cleanup_records", "command_plan_versions", "command_plans",
    "cutover_batches", "data_fixtures", "data_plan_steps", "data_plans",
    "data_requirements", "data_snapshots", "data_sources", "dataset", "dr_test_runs",
    "dsh_task", "entity_graph_snapshots", "environment_fingerprints",
    "execution_campaigns", "external_wiki_connection", "failure_hypotheses",
    "fixture_entities", "fixture_leases", "flaky_clusters", "flaky_signals",
    "generated_artifact", "governance_exceptions", "healing_proposals",
    "human_feedback", "impact_analysis_runs", "impact_results", "integration_config",
    "knowledge_iteration", "knowledge_snapshot", "knowledge_trigger_debounce",
    "legacy_case_migrations", "legacy_dataset_links", "legacy_usage_records",
    "lineage_edges", "manual_execution_sessions", "manual_execution_steps",
    "masking_profiles", "masking_rules", "mission_source_links", "missions",
    "model_evaluation_runs", "model_policies", "notification_channel",
    "notification_log", "observed_journey_steps", "observed_journeys",
    "policy_bindings", "policy_profiles", "prod_data_templates",
    "production_observation_sessions", "production_query_audits",
    "quality_gate_policies", "quality_gate_results", "regression_selection_items",
    "regression_selections", "report_template", "retention_policies", "run_profiles",
    "runtime_idempotency_keys", "scenario_gap_candidates", "scope_items",
    "secret_refs", "source_artifacts", "source_fragments", "strategy_performance",
    "sync_log", "sys_organization", "sys_organization_member",
    "template_materializations", "test_contract_versions", "test_contracts",
    "test_intents", "test_report", "triggers", "ui_asset_bindings",
    "version_mission", "wiki_diff_item", "wiki_diff_task", "wiki_lint_issue",
    "wiki_lint_report", "wiki_review_contradiction", "wiki_review_item",
    "worker_capabilities", "worker_nodes", "workflow_runs",
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())
    for table in _DROP_TABLES:
        if table in existing:
            op.drop_table(table)

    # 组织概念删除：sys_project.organization_id 列 DROP
    columns = [c['name'] for c in inspector.get_columns('sys_project')]
    if 'organization_id' in columns:
        op.drop_column('sys_project', 'organization_id')

    # version_task.source_mission_id：version_mission 表已删除，列随之外键失效 → DROP
    if 'version_task' in existing:
        vt_columns = [c['name'] for c in inspector.get_columns('version_task')]
        if 'source_mission_id' in vt_columns:
            op.drop_column('version_task', 'source_mission_id')


def downgrade() -> None:
    # 数据已销毁，无法恢复；downgrade 保持 no-op（回滚窗口内用备份恢复，见模块 docstring）
    pass
