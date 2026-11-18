"""M3 / TA-025 + AUD-004：反事实重放协调器（Experiment → 真实验证 Run）。

对齐 v1.5 §04「E1–E6 实验矩阵」与 §01 AUD-004：

- E1–E6 各自有**唯一变量**，``validate_change()`` 拒绝变量与实验不匹配的变更；
- 创建实验必须给出真实存在的 ``baseline_run_id``，只落 ``DRAFT``/``VALIDATED``；
- ``launch_experiment()`` 通过 **统一 Run 创建路径** 生成真实 ``TestRun``（复制 baseline
  的不可变快照 + 仅写入声明维度），并回填 ``verification_run_id``；
- ``COMPLETED`` 只能由 ``sync_experiment_result()`` 在验证 Run 进入终态后写入；
  Run 丢失 → ``UNKNOWN``，绝不保持 RUNNING 或伪造完成；
- ``snapshot_diff_json`` 记录唯一维度差异，多维度变化 → ``BLOCKED``。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.triage import TriageExperiment
from app.aiqe.services.run_state import TERMINAL_STATUSES

#: 实验状态机（v1.5 §01 AUD-004）。
STATUSES: tuple[str, ...] = (
    "DRAFT",
    "VALIDATED",
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "UNKNOWN",
    "CANCELLED",
)
#: 假设结论（与实验状态分开保存，v1.5 §04-7）。
RESULTS: tuple[str, ...] = ("SUPPORTED", "REFUTED", "INCONCLUSIVE")


@dataclass(frozen=True)
class ExperimentSpec:
    """E1–E6 单变量定义：``variable`` 是唯一允许变化的维度。"""

    key: str
    variable: str
    fixed: tuple[str, ...] = field(default_factory=tuple)
    purpose: str = ""


EXPERIMENTS: dict[str, ExperimentSpec] = {
    "E1": ExperimentSpec(
        "E1",
        "run_attempt",
        ("build", "profile", "fixture", "browser", "provider"),
        "FLAKY：同条件重跑检查结果稳定性",
    ),
    "E2": ExperimentSpec(
        "E2",
        "fixture_namespace",
        ("build", "environment", "browser", "provider"),
        "TEST_DATA：数据隔离检查污染/并发",
    ),
    "E3": ExperimentSpec(
        "E3",
        "upstream_mode",
        ("build", "fixture", "browser", "contract"),
        "THIRD_PARTY：Live → Recorded/Sandbox 回放",
    ),
    "E4": ExperimentSpec(
        "E4",
        "feature_flag",
        ("build", "fixture", "device", "other_flags"),
        "CROSS_FEATURE：单一 Feature/Overlay flag 对照",
    ),
    "E5": ExperimentSpec(
        "E5",
        "worker_instance",
        ("build", "fixture", "profile", "driver_version"),
        "RUNNER：更换 Worker/浏览器实例",
    ),
    "E6": ExperimentSpec(
        "E6",
        "network_profile",
        ("build", "fixture", "service", "browser", "data"),
        "NETWORK：Network Profile 对照",
    ),
}

#: baseline 与 verification 必须一致的不可变字段（单变量校验用）。
IMMUTABLE_KEYS: tuple[str, ...] = (
    "scenario_id",
    "workflow_definition_id",
    "build_ref",
    "commit_sha",
    "environment_id",
    "execution_profile_id",
    "contract_checksum",
    "workflow_checksum",
    "profile_checksum",
)


class ExperimentError(ValueError):
    """实验定义/迁移非法。"""


def spec_for(experiment_key: str) -> ExperimentSpec:
    spec = EXPERIMENTS.get(str(experiment_key or "").strip().upper())
    if spec is None:
        raise ExperimentError(f"未知实验: {experiment_key!r}（仅 E1-E6）")
    return spec


def validate_change(experiment_key: str, change: Mapping[str, Any] | None) -> tuple[str, str]:
    """校验单变量：必须恰好 1 个键，且键等于该实验的唯一变量。"""
    spec = spec_for(experiment_key)
    if not isinstance(change, Mapping) or len(change) != 1:
        raise ExperimentError("单变量实验必须且只能变更 1 个变量")
    (variable, value), = change.items()
    name = str(variable).strip()
    if not name:
        raise ExperimentError("变更变量名不能为空")
    if name != spec.variable:
        raise ExperimentError(
            f"{spec.key} 的唯一变量必须是 {spec.variable!r}，实际 {name!r}"
        )
    if value is None or str(value).strip() == "":
        raise ExperimentError("变更值不能为空")
    return name, str(value)


def _snapshot(run: TestRun) -> dict[str, Any]:
    snapshot = {
        "scenario_id": run.scenario_id,
        "workflow_definition_id": run.workflow_definition_id,
        "build_ref": run.build_ref,
        "commit_sha": run.commit_sha,
        "environment_id": run.environment_id,
        "execution_profile_id": run.execution_profile_id,
        "retest_of": run.retest_of,
        "environment_snapshot": dict(run.environment_snapshot_json or {}),
    }
    for key in ("contract_checksum", "workflow_checksum", "profile_checksum"):
        if key in (run.environment_snapshot_json or {}):
            snapshot[key] = (run.environment_snapshot_json or {})[key]
    return snapshot


def snapshot_hash(run: TestRun) -> str:
    payload = json.dumps(_snapshot(run), sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot_diff(baseline: TestRun, verification: TestRun) -> dict[str, Any]:
    """返回不可变字段与 env snapshot 的差异集合。"""
    left = _snapshot(baseline)
    right = _snapshot(verification)
    changed: list[str] = []
    for key in IMMUTABLE_KEYS:
        if left.get(key) != right.get(key):
            changed.append(key)
    left_env = left.get("environment_snapshot") or {}
    right_env = right.get("environment_snapshot") or {}
    for key in sorted(set(left_env) | set(right_env)):
        if left_env.get(key) != right_env.get(key):
            changed.append(f"environment_snapshot.{key}")
    return {"changed": sorted(set(changed))}


def create_experiment(
    db: Session,
    *,
    experiment_key: str,
    change: Mapping[str, Any],
    idempotency_key: str,
    baseline_run_id: str,
    triage_case_id: str | None = None,
    hypothesis_id: str | None = None,
    profile_id: str | None = None,
) -> TriageExperiment:
    """创建实验 Draft/Validated；必须绑定真实 baseline Run。"""
    if not str(idempotency_key or "").strip():
        raise ExperimentError("idempotency_key 不能为空")
    spec = spec_for(experiment_key)
    variable, value = validate_change(spec.key, change)

    existing = db.scalar(
        select(TriageExperiment).where(TriageExperiment.idempotency_key == str(idempotency_key))
    )
    if existing is not None:
        return existing

    baseline = db.get(TestRun, str(baseline_run_id)) if baseline_run_id else None
    if baseline is None:
        raise ExperimentError(f"baseline Run 不存在: {baseline_run_id!r}")

    row = TriageExperiment(
        project_id=baseline.project_id,
        triage_case_id=triage_case_id,
        hypothesis_id=hypothesis_id,
        experiment_key=spec.key,
        changed_variable=variable,
        changed_value=value,
        changed_dimension=spec.variable,
        baseline_run_id=baseline.id,
        profile_id=profile_id,
        baseline_snapshot_hash=snapshot_hash(baseline),
        idempotency_key=str(idempotency_key),
        status="VALIDATED",
    )
    db.add(row)
    db.flush()
    return row


def default_run_launcher(
    db: Session, experiment: TriageExperiment, baseline: TestRun
) -> str:
    """统一 Run 创建路径：复制 baseline 不可变快照，仅写入声明的单变量。"""
    if experiment.changed_dimension and experiment.changed_dimension in IMMUTABLE_KEYS:
        raise ExperimentError(f"{experiment.changed_dimension} 属于不可变字段，不能作为实验变量")
    env_snapshot = dict(baseline.environment_snapshot_json or {})
    if experiment.changed_dimension:
        env_snapshot[experiment.changed_dimension] = experiment.changed_value
    run = TestRun(
        project_id=baseline.project_id,
        run_key=f"EXP-{experiment.experiment_key}-{uuid.uuid4().hex[:12]}",
        source_type="experiment",
        source_id=experiment.id,
        scenario_id=baseline.scenario_id,
        workflow_definition_id=baseline.workflow_definition_id,
        build_ref=baseline.build_ref,
        commit_sha=baseline.commit_sha,
        environment_id=baseline.environment_id,
        execution_profile_id=experiment.profile_id or baseline.execution_profile_id,
        environment_snapshot_json=env_snapshot,
        retest_of=baseline.id,
        status="QUEUED",
    )
    db.add(run)
    db.flush()

    baseline_nodes = list(
        db.scalars(select(NodeRun).where(NodeRun.run_id == baseline.id).order_by(NodeRun.id))
    )
    if baseline_nodes:
        from app.aiqe.services import dag_scheduler

        graph = {
            "schema_version": "1.0",
            "nodes": [
                {
                    "key": node.node_key,
                    "driver": node.driver_key or "http",
                    "input": dict(node.input_ref or {}),
                    "depends_on": [],
                }
                for node in baseline_nodes
            ],
            "edges": [],
        }
        dag_scheduler.create_node_runs(db, run.id, graph)
    return run.id


def launch_experiment(
    db: Session,
    experiment_id: str,
    *,
    launcher: Callable[[Session, TriageExperiment, TestRun], str] | None = None,
) -> TriageExperiment:
    """为实验创建真实验证 Run；重复调用返回已有 Run（幂等）。"""
    row = db.get(TriageExperiment, experiment_id)
    if row is None:
        raise ExperimentError(f"实验不存在: {experiment_id!r}")
    if row.verification_run_id:
        return row

    baseline = db.get(TestRun, row.baseline_run_id) if row.baseline_run_id else None
    if baseline is None:
        row.status = "BLOCKED"
        row.error_code = "BASELINE_RUN_MISSING"
        db.flush()
        return row
    if baseline.project_id != row.project_id:
        raise ExperimentError("baseline Run 与实验不属于同一 Project")

    run_id = (launcher or default_run_launcher)(db, row, baseline)
    run = db.get(TestRun, run_id)
    if run is None:
        raise ExperimentError(f"验证 Run 创建失败: {run_id!r}")
    if run.project_id != baseline.project_id:
        raise ExperimentError("验证 Run 与 baseline Run 不属于同一 Project")

    diff = snapshot_diff(baseline, run)
    single_variable = diff["changed"] == [f"environment_snapshot.{row.changed_dimension}"]
    row.snapshot_diff_json = {
        **diff,
        "expected_dimension": row.changed_dimension,
        "single_variable": single_variable,
    }
    row.verification_run_id = run.id
    row.verification_snapshot_hash = snapshot_hash(run)
    row.started_at = datetime.now(UTC)
    if not single_variable:
        row.status = "BLOCKED"
        row.error_code = "MULTI_VARIABLE_EXPERIMENT"
    else:
        row.status = "RUNNING" if run.status in {"RUNNING", "WAITING_HUMAN", "TRIAGING"} else "QUEUED"
        row.error_code = None
    db.flush()
    return row


def sync_experiment_result(db: Session, experiment_id: str) -> TriageExperiment:
    """验证 Run 终态后收敛实验状态；不臆造结果。"""
    row = db.get(TriageExperiment, experiment_id)
    if row is None:
        raise ExperimentError(f"实验不存在: {experiment_id!r}")
    if row.status in {"BLOCKED", "CANCELLED"}:
        return row
    if not row.verification_run_id:
        row.status = "UNKNOWN"
        row.error_code = "VERIFICATION_RUN_MISSING"
        db.flush()
        return row
    run = db.get(TestRun, row.verification_run_id)
    if run is None:
        row.status = "UNKNOWN"
        row.error_code = "VERIFICATION_RUN_MISSING"
        row.completed_at = datetime.now(UTC)
        db.flush()
        return row
    if run.status not in TERMINAL_STATUSES:
        row.status = "RUNNING" if run.status in {"RUNNING", "TRIAGING"} else "QUEUED"
        db.flush()
        return row

    row.completed_at = datetime.now(UTC)
    if run.outcome is None:
        row.status = "UNKNOWN"
        row.error_code = f"RUN_TERMINAL_WITHOUT_OUTCOME:{run.status}"
    elif run.status == "ERROR":
        row.status = "FAILED"
        row.error_code = "VERIFICATION_RUN_ERROR"
    else:
        row.status = "COMPLETED"
        row.error_code = None
    db.flush()
    return row


def record_experiment_result(
    db: Session, experiment_id: str, *, result: str
) -> TriageExperiment:
    """记录假设结论；只有 COMPLETED 的实验才能给出 SUPPORTED/REFUTED/INCONCLUSIVE。"""
    if result not in RESULTS:
        raise ExperimentError(f"非法实验结论: {result!r}（仅 {RESULTS}）")
    row = db.get(TriageExperiment, experiment_id)
    if row is None:
        raise ExperimentError(f"实验不存在: {experiment_id!r}")
    if row.status != "COMPLETED":
        raise ExperimentError("实验尚未完成（需验证 Run 终态），不能记录结论")
    if not row.verification_run_id:
        raise ExperimentError("实验缺少 verification_run_id")
    row.experiment_result = result
    db.flush()
    return row


def list_experiments(db: Session, triage_case_id: str) -> list[TriageExperiment]:
    return list(
        db.scalars(
            select(TriageExperiment)
            .where(TriageExperiment.triage_case_id == triage_case_id)
            .order_by(TriageExperiment.created_at)
        )
    )


__all__ = [
    "EXPERIMENTS",
    "IMMUTABLE_KEYS",
    "RESULTS",
    "STATUSES",
    "ExperimentError",
    "ExperimentSpec",
    "create_experiment",
    "default_run_launcher",
    "launch_experiment",
    "list_experiments",
    "record_experiment_result",
    "snapshot_diff",
    "snapshot_hash",
    "spec_for",
    "sync_experiment_result",
    "validate_change",
]
