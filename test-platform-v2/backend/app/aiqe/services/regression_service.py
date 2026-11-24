"""batch-341 + AUD-009：缺陷修复回归请求（幂等 / 40 位 SHA / 部署证明 / 范围冻结）。

v1.5 §02 AUD-009 不变量：

1. ``fixed_sha`` 必须是完整 40 位 Git SHA（禁止模糊前缀）；
2. 目标环境实际运行的 SHA 只能来自 ``aiqe_deployment_attestations``（CI/部署写入），
   不接受客户端自报；不匹配 → BLOCKED；
3. 回归范围在执行前冻结（source Run 的 Workflow/Profile/Contract checksum + 强制集合），
   执行期间不随最新用例/Workflow 漂移；
4. 服务端计算 idempotency fingerprint 并加唯一约束：重复提交（含并发）只产生一个回归；
5. 旧 Run / Assertion / Artifact 只读，不被修改。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.deployment import DeploymentAttestation
from app.aiqe.services.impact_service import ImpactError
from app.aiqe.models.profile import ExecutionProfile
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.services.regression_scope import (
    ScopeError,
    build_scope_plan,
    ensure_scope_snapshot,
)
from app.aiqe.services.run_launch import launch
from app.aiqe.services.snapshot_service import (
    SnapshotError,
    clone_snapshot,
    ensure_snapshot,
    get_snapshot,
)
from typing import TYPE_CHECKING

from app.models.defect import Defect, DefectRegression

if TYPE_CHECKING:
    from app.models.defect import RunComparisonSnapshot

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SCOPES: frozenset[str] = frozenset(
    {
        "DIRECT_FAILURES",
        "DIRECT_FAILURES_PLUS_P0",
        "DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT",
        "SELECTED",
    }
)
BLOCKED_STATUS = "BLOCKED"
ACTIVE_STATUSES = frozenset({"DRAFT", "QUEUED", "RUNNING", "BLOCKED", "PENDING"})


class RegressionError(ValueError):
    pass


class RegressionNotFound(LookupError):
    pass


def normalize_sha(value: str, *, field: str = "fixed_sha") -> str:
    sha = str(value or "").strip().lower()
    if not FULL_SHA_RE.match(sha):
        raise RegressionError(f"{field} 必须是完整 40 位十六进制 Git SHA（实际 {value!r}）")
    return sha


def _fingerprint(
    *,
    project_id: int,
    defect_id: int,
    fixed_sha: str,
    deployed_sha: str,
    environment_id: int | None,
    workflow_checksum: str | None,
    scope_hash: str,
) -> str:
    payload = "|".join(
        [
            str(project_id),
            str(defect_id),
            fixed_sha,
            deployed_sha,
            str(environment_id or ""),
            workflow_checksum or "",
            scope_hash,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _scope_hash(scope: str, mandatory: list[str], selected: list[str]) -> str:
    payload = json.dumps(
        {"scope": scope, "mandatory": sorted(mandatory), "selected": sorted(selected)},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def resolve_deployed_sha(
    db: Session, *, project_id: int, environment_id: int | None
) -> str | None:
    row = db.scalar(
        select(DeploymentAttestation)
        .where(
            DeploymentAttestation.project_id == int(project_id),
            DeploymentAttestation.environment_id == environment_id,
        )
        .order_by(DeploymentAttestation.attested_at.desc())
    )
    return row.commit_sha if row is not None else None


def record_deployment_attestation(
    db: Session,
    *,
    project_id: int,
    environment_id: int | None,
    commit_sha: str,
    image_digest: str = "",
    source: str = "ci",
    evidence_ref: str = "",
    attested_by: int | None = None,
    attested_at: datetime | None = None,
) -> DeploymentAttestation:
    sha = normalize_sha(commit_sha, field="commit_sha")
    row = DeploymentAttestation(
        project_id=int(project_id),
        environment_id=environment_id,
        commit_sha=sha,
        image_digest=image_digest,
        source=source,
        evidence_ref=evidence_ref,
        attested_by=attested_by,
        attested_at=attested_at or datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return row


def _failed_case_refs(db: Session, run_id: str) -> list[str]:
    """source Run 的直接失败集合（节点 key + 失败断言 key）。"""
    refs: list[str] = []
    nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    for node in nodes:
        if node.status in {"FAILED", "BLOCKED"}:
            refs.append(f"node:{node.node_key}")
    rows = db.execute(
        select(RunAssertionResult)
        .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
        .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
        .where(NodeRun.run_id == run_id, RunAssertionResult.status.in_(["FAIL", "BLOCKED", "ERROR"]))
    ).all()
    for (assertion,) in rows:
        refs.append(f"assertion:{assertion.assertion_key}")
    return sorted(set(refs))


def build_mandatory_scope(
    db: Session,
    *,
    source_run: TestRun | None,
    scope: str,
    selected_case_ids: list[str] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """强制集合：AI 不可删除；被排除项必须给出机器可查 reason。"""
    mandatory: list[str] = []
    excluded: list[dict[str, Any]] = []
    if source_run is not None:
        mandatory.extend(_failed_case_refs(db, source_run.id))
    selected = list(selected_case_ids or [])
    if scope == "SELECTED":
        mandatory.extend(selected)
    elif scope in {"DIRECT_FAILURES_PLUS_P0", "DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT"}:
        mandatory.extend(item for item in selected if item.upper().startswith("P0"))
        excluded.extend(
            {"case_id": item, "reason": "NON_P0_NOT_IN_MANDATORY_SCOPE"}
            for item in selected
            if not item.upper().startswith("P0")
        )
    return sorted(set(mandatory)), excluded


def _source_snapshot(db: Session, source_run: TestRun | None) -> dict[str, Any]:
    if source_run is None:
        return {}
    workflow_checksum: str | None = None
    if source_run.workflow_definition_id:
        definition = db.get(WorkflowDefinition, source_run.workflow_definition_id)
        workflow_checksum = definition.checksum if definition is not None else None
    profile_checksum: str | None = None
    if source_run.execution_profile_id:
        profile = db.get(ExecutionProfile, source_run.execution_profile_id)
        profile_checksum = profile.checksum if profile is not None else None
    return {
        "scenario_id": source_run.scenario_id,
        "workflow_definition_id": source_run.workflow_definition_id,
        "workflow_checksum": workflow_checksum,
        "profile_checksum": profile_checksum,
        "build_ref": source_run.build_ref,
        "commit_sha": source_run.commit_sha,
        "environment_id": source_run.environment_id,
    }


def _regression_snapshot(db: Session, source_run: TestRun | None, snapshot: dict[str, Any]):
    """解析 source Run 的不可变快照；缺失时返回 None（由调用方 BLOCKED）。"""
    if source_run is not None and source_run.workflow_snapshot_id:
        try:
            return get_snapshot(
                db, source_run.workflow_snapshot_id, project_id=int(source_run.project_id)
            )
        except SnapshotError:
            return None
    workflow_id = snapshot.get("workflow_definition_id")
    if workflow_id:
        definition = db.get(WorkflowDefinition, workflow_id)
        if definition is not None:
            return ensure_snapshot(db, definition)
    return None


def _replicate_nodes(db: Session, *, source_run: TestRun | None, target_run: TestRun) -> None:
    if source_run is None:
        return
    nodes = list(
        db.scalars(select(NodeRun).where(NodeRun.run_id == source_run.id).order_by(NodeRun.id))
    )
    if not nodes:
        return
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
            for node in nodes
        ],
        "edges": [],
    }
    dag_scheduler.create_node_runs(db, target_run.id, graph)


def compute_impact_analysis(base_sha: str, head_sha: str) -> dict[str, Any]:
    """服务端重算影响分析（V16-014：禁止只信任调用方提交的 impact_analysis）。"""
    from app.aiqe.services.change_impact import analyze_change_impact
    from app.aiqe.services.impact_service import _run_git, collect_changes

    base = normalize_sha(base_sha, field="base_sha")
    head = normalize_sha(head_sha, field="fixed_sha")
    if base == head:
        raise RegressionError("base_sha 与 fixed_sha 不能相同")
    repo_root = Path(__file__).resolve().parents[5]
    files, _symbols, _routes, _migrations, _components = collect_changes(
        str(repo_root), base, head
    )
    if not files:
        raise RegressionError("服务端无法计算影响：diff 为空或 SHA 不在仓库历史中")
    diff_text = _run_git(str(repo_root), ["diff", "--unified=0", f"{base}..{head}"])
    return analyze_change_impact(
        base_sha=base,
        head_sha=head,
        changed_files=[item.path for item in files],
        diff_text=diff_text[:200_000],
        repo_root=str(repo_root),
    )


def create_regression_request(
    db: Session,
    *,
    project_id: int,
    defect_id: int,
    fixed_sha: str,
    target_environment_id: int | None = None,
    source_run_id: str | None = None,
    scope: str = "DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT",
    selected_case_ids: list[str] | None = None,
    reason: str = "",
    idempotency_key: str | None = None,
    actor_id: int | None = None,
    impact_analysis: Mapping[str, Any] | None = None,
    impact_base_sha: str | None = None,
) -> tuple[DefectRegression, TestRun | None, bool]:
    """返回 ``(regression, verification_run, created)``；BLOCKED 时 run 为 None。"""
    sha = normalize_sha(fixed_sha)
    if scope not in SCOPES:
        raise RegressionError(f"未知 scope: {scope!r}（允许 {sorted(SCOPES)}）")
    defect = db.get(Defect, defect_id)
    if defect is None or int(defect.project_id or 0) != int(project_id):
        raise RegressionError(f"缺陷不存在: {defect_id}")

    source_run: TestRun | None = None
    if source_run_id:
        source_run = db.get(TestRun, source_run_id)
        if source_run is None or int(source_run.project_id or 0) != int(project_id):
            raise RegressionError(f"source Run 不存在: {source_run_id}")
    environment_id = (
        int(target_environment_id)
        if target_environment_id is not None
        else (source_run.environment_id if source_run is not None else None)
    )

    mandatory, excluded = build_mandatory_scope(
        db, source_run=source_run, scope=scope, selected_case_ids=selected_case_ids
    )
    snapshot = _source_snapshot(db, source_run)
    frozen = _regression_snapshot(db, source_run, snapshot)
    workflow_checksum = (
        frozen.checksum_sha256 if frozen is not None else snapshot.get("workflow_checksum")
    )
    scope_plan: dict[str, Any] | None = None
    blockers_scope_error: dict[str, str] | None = None
    impact_meta: dict[str, Any] | None = None
    impact_error: dict[str, str] | None = None
    analysis: Mapping[str, Any] | None = impact_analysis
    server_analysis: dict[str, Any] | None = None
    if impact_base_sha:
        # 服务端重算：调用方只提供 base SHA，分析内容由服务器从真实 Git 历史推导。
        try:
            server_analysis = compute_impact_analysis(str(impact_base_sha), sha)
        except (RegressionError, ValueError, ImpactError) as exc:
            impact_error = {
                "code": "IMPACT_ANALYSIS_UNCOMPUTABLE",
                "message": str(exc)[:300],
            }
        else:
            if (
                impact_analysis is not None
                and str(impact_analysis.get("checksum") or "")
                != str(server_analysis.get("checksum") or "")
            ):
                impact_error = {
                    "code": "IMPACT_ANALYSIS_MISMATCH",
                    "message": "调用方 impact_analysis 与服务端重算的 checksum 不一致",
                }
            else:
                analysis = server_analysis
    if analysis is not None and impact_error is None:
        from app.aiqe.services.case_catalog import (
            CaseCatalogError,
            match_impact,
            verify_analysis,
        )

        try:
            verify_analysis(analysis)
            graph_keys = {
                str(node.get("key"))
                for node in (frozen.canonical_json if frozen is not None else {}).get("nodes") or []
            }
            matched = match_impact(
                db,
                project_id=int(project_id),
                impact_analysis=analysis,
                allowed_node_keys=graph_keys,
            )
            mandatory = sorted(set(mandatory) | set(matched["node_refs"]))
            impact_meta = {
                "status": matched["status"],
                "checksum": analysis.get("checksum"),
                "matched_case_ids": matched["matched_case_ids"],
                "node_refs": matched["node_refs"],
                "catalog_size": matched["catalog_size"],
                "unknown_broadened": matched["unknown_broadened"],
                # V16-014：区分服务端重算与调用方提交，禁止把调用方数据当 A5 结果。
                "source": "server" if server_analysis is not None else "caller",
                "base_sha": analysis.get("base_sha"),
                "head_sha": analysis.get("head_sha"),
            }
        except CaseCatalogError as exc:
            impact_error = {"code": "IMPACT_ANALYSIS_INVALID", "message": str(exc)}
    scope_hash = _scope_hash(scope, mandatory, list(selected_case_ids or []))
    if frozen is not None:
        try:
            scope_plan = build_scope_plan(
                scope=scope,
                graph=frozen.canonical_json or {},
                mandatory_refs=list(mandatory),
                excluded=list(excluded),
                inputs={
                    "source_run_id": source_run.id if source_run is not None else None,
                    "workflow_snapshot_id": frozen.id,
                    "snapshot_hash": frozen.checksum_sha256,
                    "fixed_sha": sha,
                    "environment_id": environment_id,
                    "selected_case_ids": list(selected_case_ids or []),
                },
            )
            scope_hash = str(scope_plan["checksum_sha256"])
        except ScopeError as exc:
            scope_plan = None
            blockers_scope_error = {"code": exc.code, "message": str(exc)}
        else:
            blockers_scope_error = None
    else:
        blockers_scope_error = None

    blockers: list[dict[str, Any]] = []
    if impact_error is not None:
        blockers.append(impact_error)
    if blockers_scope_error is not None:
        blockers.append(blockers_scope_error)
    deployed_sha = resolve_deployed_sha(
        db, project_id=int(project_id), environment_id=environment_id
    )
    if deployed_sha is None:
        blockers.append(
            {
                "code": "DEPLOYMENT_ATTESTATION_MISSING",
                "message": "目标环境没有可信部署记录，无法证明 fixed SHA 已部署",
                "environment_id": environment_id,
            }
        )
    elif normalize_sha(deployed_sha, field="deployed_sha") != sha:
        blockers.append(
            {
                "code": "DEPLOYED_SHA_MISMATCH",
                "message": "目标环境实际部署版本与 fixed SHA 不一致",
                "deployed_sha": deployed_sha,
                "fixed_sha": sha,
            }
        )

    if frozen is None:
        blockers.append(
            {
                "code": "SOURCE_SNAPSHOT_MISSING",
                "message": "source Run 未绑定不可变 WorkflowSnapshot，无法重建回归 DAG",
                "source_run_id": source_run.id if source_run is not None else None,
            }
        )
    fingerprint_seed = _fingerprint(
        project_id=int(project_id),
        defect_id=int(defect_id),
        fixed_sha=sha,
        deployed_sha=deployed_sha or "",
        environment_id=environment_id,
        workflow_checksum=workflow_checksum,
        scope_hash=scope_hash,
    )

    existing = db.scalar(
        select(DefectRegression).where(
            DefectRegression.idempotency_fingerprint == fingerprint_seed
        )
    )
    if existing is not None:
        verification = (
            db.get(TestRun, existing.verification_run_id)
            if existing.verification_run_id
            else None
        )
        return existing, verification, False

    now = datetime.now(UTC)
    row = DefectRegression(
        defect_id=int(defect_id),
        fixed_sha=sha,
        previous_run_id=source_run.id if source_run is not None else None,
        source_run_id=source_run.id if source_run is not None else None,
        deployed_sha=deployed_sha or "",
        target_environment_id=environment_id,
        workflow_definition_id=snapshot.get("workflow_definition_id"),
        workflow_checksum=workflow_checksum,
        profile_checksum=snapshot.get("profile_checksum"),
        scope=scope,
        scope_hash=scope_hash,
        mandatory_case_ids_json=mandatory,
        selected_case_ids_json=list(selected_case_ids or []),
        excluded_json=excluded,
        reason=str(reason or "")[:2000],
        request_idempotency_key=(str(idempotency_key)[:128] if idempotency_key else None),
        idempotency_fingerprint=fingerprint_seed,
        blockers_json=blockers or None,
        status=BLOCKED_STATUS if blockers else "QUEUED",
        created_at=now,
    )
    db.add(row)
    db.flush()
    if scope_plan is not None and not blockers:
        scope_row = ensure_scope_snapshot(
            db,
            project_id=int(project_id),
            defect_id=int(defect_id),
            plan=scope_plan,
            approved_by=actor_id,
        )
        row.scope_snapshot_id = scope_row.id
        row.scope_hash = scope_row.checksum_sha256
        scope_plan["scope_id"] = scope_row.id

    if blockers:
        return row, None, True

    # V16-006/007：回归必须经统一 Launch + 冻结快照（禁止手写 NodeRun 复制）。
    assert frozen is not None
    child = clone_snapshot(db, frozen, execution_kind="DEFECT_REGRESSION")
    launch_result = launch(
        db,
        project_id=int(project_id),
        user_id=actor_id,
        workflow_snapshot_id=child.id,
        execution_kind="DEFECT_REGRESSION",
        scope_snapshot=scope_plan,
        launch_key=f"regression:{row.id}",
        source_type="regression",
        source_id=str(defect_id),
        retest_of=source_run.id if source_run is not None else None,
        commit_sha=sha,
        build_ref=snapshot.get("build_ref") or "",
        environment_id=environment_id,
        execution_profile_id=(
            source_run.execution_profile_id if source_run is not None else None
        ),
        environment_snapshot={
            "fixed_sha": sha,
            "deployed_sha": deployed_sha,
            "defect_id": defect_id,
            "source_run_id": source_run.id if source_run is not None else None,
            "workflow_checksum": workflow_checksum,
            "profile_checksum": snapshot.get("profile_checksum"),
            "scope": scope,
            "scope_hash": scope_hash,
            "mandatory_case_ids": mandatory,
            "regression_id": row.id,
            "impact_analysis": impact_meta,
        },
    )
    run = db.get(TestRun, launch_result.run_id)
    if run is None:
        raise RegressionError("回归 Run 创建失败")
    row.verification_run_id = run.id
    row.workflow_checksum = run.workflow_checksum
    if launch_result.dispatch_status == "BLOCKED":
        row.status = BLOCKED_STATUS
        row.blockers_json = [
            {
                "code": launch_result.blocked_reason or "PREFLIGHT_BLOCKED",
                "message": "回归 Run 在 Preflight 阶段被阻断",
            }
        ]
    else:
        row.status = "QUEUED"

    from app.aiqe.services import dag_scheduler

    dag_scheduler.emit_event(
        db,
        run_id=run.id,
        event_type="regression.created",
        payload={
            "regression_id": row.id,
            "defect_id": defect_id,
            "fixed_sha": sha,
            "deployed_sha": deployed_sha,
            "scope": scope,
            "scope_hash": scope_hash,
            "mandatory_case_ids": mandatory[:100],
            "source_run_id": source_run.id if source_run is not None else None,
            "actor_id": actor_id,
        },
        producer_event_id=f"regression:{row.id}:created",
    )
    db.flush()
    return row, run, True


def cancel_regression(
    db: Session, *, regression_id: int, project_id: int, reason: str = ""
) -> DefectRegression:
    row = get_regression(db, regression_id, project_id)
    if row.status in {"PASS", "FAIL", "CANCELLED", "UNKNOWN"}:
        raise RegressionError(f"回归已终结，不能取消: {row.status}")
    row.status = "CANCELLED"
    row.cancelled_at = datetime.now(UTC)
    row.terminal_summary_json = {**(row.terminal_summary_json or {}), "cancel_reason": reason}
    run = db.get(TestRun, row.verification_run_id) if row.verification_run_id else None
    if run is not None and run.status in {"DRAFT", "QUEUED", "RUNNING"}:
        from app.aiqe.services.run_state import apply_transition

        try:
            apply_transition(run, "CANCELED")
        except Exception:  # 状态机不允许时保留原状，仅取消回归请求
            pass
    db.flush()
    return row


def get_regression(db: Session, regression_id: int, project_id: int) -> DefectRegression:
    row = db.get(DefectRegression, regression_id)
    if row is None:
        raise RegressionNotFound(str(regression_id))
    defect = db.get(Defect, row.defect_id)
    if defect is None or int(defect.project_id or 0) != int(project_id):
        raise RegressionNotFound(str(regression_id))
    return row


def list_regressions(
    db: Session, project_id: int, *, defect_id: int | None = None, limit: int = 100
) -> list[DefectRegression]:
    stmt = (
        select(DefectRegression)
        .join(Defect, Defect.id == DefectRegression.defect_id)
        .where(Defect.project_id == project_id)
        .order_by(DefectRegression.created_at.desc())
        .limit(limit)
    )
    if defect_id is not None:
        stmt = stmt.where(DefectRegression.defect_id == defect_id)
    return list(db.scalars(stmt))


def get_verification_run(db: Session, row: DefectRegression) -> TestRun | None:
    if not row.verification_run_id:
        return None
    return db.get(TestRun, row.verification_run_id)


def create_regression(
    db: Session,
    *,
    project_id: int,
    defect_id: int,
    fixed_sha: str,
    previous_run_id: str | None = None,
    environment_snapshot: dict | None = None,
) -> tuple[DefectRegression, TestRun]:
    """向后兼容包装（旧调用只传 previous_run_id）。"""
    row, run, _created = create_regression_request(
        db,
        project_id=project_id,
        defect_id=defect_id,
        fixed_sha=fixed_sha,
        source_run_id=previous_run_id,
        selected_case_ids=[],
    )
    if run is None:
        raise RegressionError(f"回归被阻断: {row.blockers_json}")
    del environment_snapshot
    return row, run


def load_comparison(
    db: Session, *, regression_id: int, project_id: int
) -> tuple[DefectRegression, RunComparisonSnapshot | None]:
    """返回 (regression, comparison_snapshot)；必要时先幂等收敛一次终端状态。"""
    from app.models.defect import RunComparisonSnapshot

    row = get_regression(db, regression_id, project_id)
    snapshot = None
    if row.comparison_snapshot_id:
        snapshot = db.get(RunComparisonSnapshot, row.comparison_snapshot_id)
    if snapshot is None and row.verification_run_id:
        from app.aiqe.services.regression_terminal import handle_run_terminal

        handle_run_terminal(db, run_id=row.verification_run_id)
        db.commit()
        db.refresh(row)
        if row.comparison_snapshot_id:
            snapshot = db.get(RunComparisonSnapshot, row.comparison_snapshot_id)
    return row, snapshot