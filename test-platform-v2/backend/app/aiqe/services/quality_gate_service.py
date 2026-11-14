"""v1.4 FIX-012：Quality Gate 从持久化事实派生（不接受前端计数）。

事实来源：
- TestRun（项目隔离、build/env 过滤）→ NodeRun → StepAttempt → RunAssertionResult；
- 只统计 severity=P0 的断言；
- 同一 node 的同一 assertion 取最新 attempt（历史失败保留，但不覆盖当前结论）；
- 结果写入 `aiqe_quality_gate_snapshots`（append-only，不允许更新历史）。

P0 规则：
- 任意 FAIL → FAIL；
- 任意 UNKNOWN / NOT_EVALUATED / BLOCKED / ERROR → BLOCKED；
- 全部 PASS 且至少一条 P0 → PASS；
- 没有 P0 → BLOCKED。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.gate import QualityGateSnapshot
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.models.version_task import VersionTask

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
RULE_VERSION = "v1.4-facts"


class GateError(ValueError):
    pass


class GateNotFound(LookupError):
    pass


def _latest_attempts(db: Session, node_ids: list[str]) -> dict[str, StepAttempt]:
    if not node_ids:
        return {}
    rows = list(
        db.scalars(
            select(StepAttempt)
            .where(StepAttempt.node_run_id.in_(node_ids))
            .order_by(StepAttempt.node_run_id, StepAttempt.attempt_no)
        )
    )
    latest: dict[str, StepAttempt] = {}
    for row in rows:
        latest[row.node_run_id] = row
    return latest


def _runs_for_scope(
    db: Session,
    *,
    project_id: int,
    run_ids: list[str] | None,
    version_task_id: int | None,
    build_ref: str = "",
    environment_ref: str = "",
) -> list[TestRun]:
    stmt = select(TestRun).where(TestRun.project_id == project_id)
    if run_ids:
        stmt = stmt.where(TestRun.id.in_(run_ids))
    elif version_task_id is not None:
        stmt = stmt.where(
            TestRun.source_type == "version_task",
            TestRun.source_id == str(version_task_id),
        )
    else:
        raise GateError("必须提供 run_ids 或 version_task_id")
    if build_ref:
        stmt = stmt.where(TestRun.build_ref == build_ref)
    if environment_ref:
        stmt = stmt.where(TestRun.environment_id == int(environment_ref))
    return list(db.scalars(stmt.order_by(TestRun.created_at.desc())))


def evaluate_from_facts(
    db: Session,
    *,
    project_id: int,
    run_ids: list[str] | None = None,
    version_task_id: int | None = None,
    build_ref: str = "",
    environment_ref: str = "",
    computed_by: int | None = None,
) -> QualityGateSnapshot:
    if version_task_id is not None:
        task = db.get(VersionTask, version_task_id)
        if task is None or int(task.project_id or 0) != int(project_id):
            raise GateNotFound(f"VersionTask 不存在: {version_task_id}")
    runs = _runs_for_scope(
        db,
        project_id=project_id,
        run_ids=run_ids,
        version_task_id=version_task_id,
        build_ref=build_ref,
        environment_ref=environment_ref,
    )
    if run_ids:
        found = {run.id for run in runs}
        missing = [run_id for run_id in run_ids if run_id not in found]
        if missing:
            raise GateNotFound(f"Run 不存在或不属于当前项目: {missing[0]}")
    if not runs:
        snapshot = QualityGateSnapshot(
            project_id=project_id,
            version_task_id=version_task_id,
            gate_status=BLOCKED,
            rule_version=RULE_VERSION,
            build_ref=build_ref,
            environment_ref=environment_ref,
            p0_total=0,
            p0_passed=0,
            p0_failed=0,
            p0_blocked=0,
            source_ids_json=[],
            snapshot_json={"reason": "NO_RUNS"},
            reasons_json=["没有符合 Build/Environment 的 Run，门禁不能判定"],
            computed_at=datetime.now(UTC),
            computed_by=computed_by,
        )
        db.add(snapshot)
        db.flush()
        return snapshot

    run_ids_found = [run.id for run in runs]
    nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id.in_(run_ids_found))))
    latest = _latest_attempts(db, [node.id for node in nodes])
    attempt_ids = [attempt.id for attempt in latest.values()]
    assertions = (
        list(
            db.scalars(
                select(RunAssertionResult).where(
                    RunAssertionResult.step_attempt_id.in_(attempt_ids),
                    RunAssertionResult.severity == "P0",
                )
            )
        )
        if attempt_ids
        else []
    )
    by_key: dict[tuple[str, str], RunAssertionResult] = {}
    for row in assertions:
        attempt = next(
            (item for item in latest.values() if item.id == row.step_attempt_id), None
        )
        if attempt is None:
            continue
        node = next((item for item in nodes if item.id == attempt.node_run_id), None)
        if node is None:
            continue
        by_key[(node.node_key, row.assertion_key)] = row

    statuses = [str(row.status).upper() for row in by_key.values()]
    passed = statuses.count(PASS)
    failed = statuses.count(FAIL)
    blocked = len(statuses) - passed - failed
    reasons: list[str] = []
    if not statuses:
        gate_status = BLOCKED
        reasons.append("没有 P0 断言事实，门禁不能判定")
    elif failed:
        gate_status = FAIL
        reasons.append(f"{failed} 条 P0 断言失败")
    elif blocked:
        gate_status = BLOCKED
        reasons.append(f"{blocked} 条 P0 断言为 BLOCKED/ERROR/NOT_EVALUATED")
    else:
        gate_status = PASS

    contract_checksums = {
        str(run.workflow_checksum or "") for run in runs if run.workflow_checksum
    }
    snapshot = QualityGateSnapshot(
        project_id=project_id,
        version_task_id=version_task_id,
        gate_status=gate_status,
        rule_version=RULE_VERSION,
        build_ref=build_ref,
        environment_ref=environment_ref,
        contract_checksum=(
            next(iter(contract_checksums)) if len(contract_checksums) == 1 else ""
        ),
        p0_total=len(statuses),
        p0_passed=passed,
        p0_failed=failed,
        p0_blocked=blocked,
        source_ids_json=run_ids_found,
        snapshot_json={
            "run_ids": run_ids_found,
            "assertions": [
                {
                    "node_key": node_key,
                    "assertion_key": assertion_key,
                    "status": row.status,
                    "oracle_layer": row.oracle_layer,
                    "oracle_ref": row.oracle_ref,
                }
                for (node_key, assertion_key), row in sorted(by_key.items())
            ],
            "contract_checksums": sorted(contract_checksums),
        },
        reasons_json=reasons,
        computed_at=datetime.now(UTC),
        computed_by=computed_by,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def snapshot_dict(row: QualityGateSnapshot) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "version_task_id": row.version_task_id,
        "gate_status": row.gate_status,
        "rule_version": row.rule_version,
        "build_ref": row.build_ref,
        "environment_ref": row.environment_ref,
        "contract_checksum": row.contract_checksum,
        "p0_total": row.p0_total,
        "p0_passed": row.p0_passed,
        "p0_failed": row.p0_failed,
        "p0_blocked": row.p0_blocked,
        "source_ids": row.source_ids_json or [],
        "reasons": row.reasons_json or [],
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        "immutable": True,
    }


def latest_snapshot(
    db: Session, *, project_id: int, version_task_id: int | None = None
) -> QualityGateSnapshot | None:
    stmt = select(QualityGateSnapshot).where(
        QualityGateSnapshot.project_id == project_id
    )
    if version_task_id is not None:
        stmt = stmt.where(QualityGateSnapshot.version_task_id == version_task_id)
    return db.scalar(
        stmt.order_by(QualityGateSnapshot.computed_at.desc()).limit(1)
    )
