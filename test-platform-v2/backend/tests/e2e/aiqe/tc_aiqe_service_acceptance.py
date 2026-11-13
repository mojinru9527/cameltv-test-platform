"""TC-AIQE-001..010 服务层验收（隔离 Test backend 容器内执行，真实 PostgreSQL）。

运行（服务器）：
  docker cp tc_aiqe_service_acceptance.py aiqe-test-backend:/tmp/
  docker exec aiqe-test-backend python /tmp/tc_aiqe_service_acceptance.py

说明：本脚本直接调用 AIQE 服务层（与 API 同一套服务），在 Test 库上创建隔离数据并清理；
无法由当前服务边界真实覆盖的场景标记 BLOCKED，不造假绿。
"""
from __future__ import annotations

import json
import traceback
import uuid
from typing import Any

from sqlalchemy import delete, select

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.learning import BugPattern, LearningCandidate
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.services import (
    capability_registry,
    dag_scheduler,
    event_service,
    hardening_service,
    interference_service,
    learning_service,
    resource_lock,
    workflow_service,
)
from app.aiqe.services.platform_matrix import build_platform_matrix
from app.core.db import SessionLocal
from app.models.project import Project

RESULTS: list[dict[str, Any]] = []
CLEANUP: list[tuple[str, str]] = []


def project_id(db) -> int:
    pid = db.scalar(select(Project.id).order_by(Project.id))
    if pid is None:
        raise RuntimeError("Test 库没有项目，无法执行")
    return int(pid)


def run_case(case_id: str, title: str, fn) -> None:
    db = SessionLocal()
    try:
        detail = fn(db) or {}
        RESULTS.append({"id": case_id, "title": title, "status": "PASS", "detail": detail})
    except NotImplementedError as exc:
        db.rollback()
        RESULTS.append(
            {"id": case_id, "title": title, "status": "BLOCKED", "reason": str(exc)}
        )
    except Exception as exc:  # noqa: BLE001 — 验收脚本需要记录失败原因
        db.rollback()
        RESULTS.append(
            {
                "id": case_id,
                "title": title,
                "status": "FAIL",
                "reason": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc(limit=4),
            }
        )
    finally:
        db.close()


def new_run(db, pid: int, tag: str, status: str = "QUEUED") -> TestRun:
    run = TestRun(
        project_id=pid,
        run_key=f"TC-AIQE-{tag}-{uuid.uuid4().hex[:8]}",
        source_type="manual",
        status=status,
    )
    db.add(run)
    db.flush()
    CLEANUP.append(("run", run.id))
    return run


GRAPH_TWO_NODES = {
    "schema_version": "1.0",
    "nodes": [
        {"key": "api", "driver": "http"},
        {"key": "ui", "driver": "playwright"},
    ],
    "edges": [{"from": "api", "to": "ui"}],
}


def tc001(db):
    """契约/定义冻结：approved 后 checksum 不变且禁止修改。"""
    if not hasattr(workflow_service, "create_workflow"):
        raise RuntimeError("workflow_service 缺失")
    graph = {
        "schema_version": "1.0",
        "nodes": [{"key": "n1", "driver": "http"}],
        "edges": [],
    }
    row = workflow_service.create_workflow(db, project_id=project_id(db), graph=graph)
    before = row.checksum
    workflow_service.approve_workflow(db, row.id, approved_by=None)
    CLEANUP.append(("workflow", row.id))
    try:
        workflow_service.update_graph(
            db, row.id, {"schema_version": "1.0", "nodes": [], "edges": []}
        )
        raise AssertionError("approved workflow 仍可修改")
    except workflow_service.WorkflowImmutableError:
        pass
    db.commit()
    return {"workflow": row.id, "checksum": before[:12], "frozen": True}


def tc002(db):
    """统一 Run：DAG 两节点依次执行，Run=PASS，事件时间线可读。"""
    pid = project_id(db)
    run = new_run(db, pid, "002")
    dag_scheduler.create_node_runs(db, run.id, GRAPH_TWO_NODES)
    dag_scheduler.schedule(db, run.id, GRAPH_TWO_NODES)
    for node in ("api", "ui"):
        dag_scheduler.mark_running(db, run.id, node)
        dag_scheduler.complete_node(db, run.id, node, "PASSED", GRAPH_TWO_NODES)
    event_service.append_event(
        db,
        run_id=run.id,
        event_type="run.started",
        payload={"schema_version": "1.0"},
        producer="system",
        producer_event_id=f"{run.run_key}-1",
    )
    db.commit()
    db.refresh(run)
    events = event_service.list_events(db, run.id)
    assert run.status == "COMPLETED" and run.outcome == "PASS", (run.status, run.outcome)
    assert len(events) >= 1, "事件时间线为空"
    return {"run": run.run_key, "status": run.status, "outcome": run.outcome, "events": len(events)}


def tc003(db):
    raise NotImplementedError(
        "首次失败+重试的 attempt 时间线由 executor/worker（真实 driver 执行）产生；"
        "Test 实例 WORKER_EXECUTION_ENABLED=false，服务层无 attempt 重试 API，需真实执行引擎"
    )


def tc004(db):
    raise NotImplementedError(
        "广告浮层交叉干扰需要业务 Web Test 目标 + integration profile 注入；"
        "当前 Test 实例无被测业务账号（Web 端此前因反爬阻断），无法真实注入"
    )


def tc005(db):
    """并发数据污染：同一 fixture 锁二次 acquire 必须被拒绝。"""
    key = f"fixture:tc-e2e-{uuid.uuid4().hex[:8]}"
    token = resource_lock.acquire(db, key, "run-a", ttl_seconds=60)
    try:
        try:
            resource_lock.acquire(db, key, "run-b", ttl_seconds=60)
            raise AssertionError("并发 acquire 未被拒绝")
        except resource_lock.LockUnavailable:
            pass
    finally:
        resource_lock.release(db, key, token)
    db.commit()
    return {"mutex": True, "key": key}


def tc006(db):
    """上游第三方故障：5xx 检测 + 节点 BLOCKED → Run 不得 PASS。"""
    sig = interference_service.dependency_5xx(
        {"dependency": {"upstream_5xx": 1, "http_5xx_rate": 0.2}}
    )
    assert sig is not None and sig.kind == "dependency_5xx", sig

    pid = project_id(db)
    run = new_run(db, pid, "006")
    graph = {
        "schema_version": "1.0",
        "nodes": [{"key": "api", "driver": "http"}],
        "edges": [],
    }
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(db, run.id, graph)
    dag_scheduler.mark_running(db, run.id, "api")
    dag_scheduler.complete_node(
        db, run.id, "api", "BLOCKED", graph, error_class="UPSTREAM_5XX"
    )
    db.commit()
    db.refresh(run)
    assert run.outcome != "PASS", f"上游 504 仍判 PASS: {run.outcome}"
    return {"signal": sig.kind, "run_outcome": run.outcome}


def tc007(db):
    """UI Runner 自身故障：worker 丢失 → 节点 BLOCKED/WORKER_LOST，Run 不 PASS。"""
    pid = project_id(db)
    run = new_run(db, pid, "007", status="RUNNING")
    node = NodeRun(
        run_id=run.id,
        node_key="ui",
        driver_key="playwright",
        status="RUNNING",
    )
    db.add(node)
    db.flush()
    out = hardening_service.recover_after_worker_kill(db, run.id, reason="tc-e2e kill")
    db.commit()
    db.refresh(node)
    db.refresh(run)
    assert node.status == "BLOCKED" and node.error_class == "WORKER_LOST", (
        node.status,
        node.error_class,
    )
    assert run.outcome != "PASS"
    return {"node": node.status, "error_class": node.error_class, "run": out}


def tc008(db):
    raise NotImplementedError(
        "缺陷草稿→人工确认→一键回归需要 UI/缺陷链路与指定 SHA 部署；"
        "AIQE 当前 HTTP 面未暴露 RegressionRequest 创建端点（P1 仅读 Console）"
    )


def tc009(db):
    """多端 AC 对照：节点能力×平台矩阵按 evidence 判定可用性。"""
    web_id = f"tc-e2e-web-{uuid.uuid4().hex[:6]}"
    android_id = f"tc-e2e-android-{uuid.uuid4().hex[:6]}"
    capability_registry.register_manifest(
        db,
        node_id=web_id,
        driver_key="playwright",
        capabilities=["browser.chromium"],
        platforms=["web"],
        evidence_ref="tc-e2e://web",
    )
    capability_registry.register_manifest(
        db,
        node_id=android_id,
        driver_key="appium",
        capabilities=["browser.chromium", "device.android"],
        platforms=["android"],
        evidence_ref="",
    )
    db.commit()
    CLEANUP.append(("node", web_id))
    CLEANUP.append(("node", android_id))

    matrix = build_platform_matrix(db)
    row = next(r for r in matrix["rows"] if r["capability"] == "browser.chromium")
    web_cell = row["cells"].get("web", {})
    android_cell = row["cells"].get("android", {})
    assert web_cell.get("available") is True, web_cell
    assert android_cell.get("available") is False, android_cell
    return {
        "platforms": matrix["platforms"],
        "web": web_cell,
        "android": android_cell,
    }


def tc010(db):
    """学习候选状态机：candidate→benchmarked→approved→active，低误报才发布。"""
    pid = project_id(db)
    pattern = f"tc-e2e-pattern-{uuid.uuid4().hex[:8]}"
    cand = learning_service.create_candidate(
        db, project_id=pid, rule={"pattern": pattern}, source="bug"
    )
    CLEANUP.append(("candidate", cand.id))
    learning_service.evaluate_candidate(
        db, cand.id, {"false_positive_rate": 0.05, "sample_size": 50}
    )
    learning_service.approve_candidate(db, cand.id)
    pattern_row = learning_service.activate_candidate(db, cand.id)
    db.commit()
    db.refresh(cand)
    if pattern_row is not None:
        CLEANUP.append(("bugpattern", pattern_row.pattern_key))
    assert cand.status == "active", cand.status
    assert pattern_row is not None, "ACTIVE 后未生成 BugPattern"
    return {"candidate": cand.id, "status": cand.status, "pattern": pattern_row.pattern_key}


CASES = [
    ("TC-AIQE-001", "需求契约冻结 + 变更影响（定义冻结代理）", tc001),
    ("TC-AIQE-002", "统一 Run（DAG + 事件时间线）", tc002),
    ("TC-AIQE-003", "首次失败 + 重试成功 → 不掩盖失败", tc003),
    ("TC-AIQE-004", "广告浮层交叉干扰", tc004),
    ("TC-AIQE-005", "并发数据污染（fixture 锁互斥）", tc005),
    ("TC-AIQE-006", "上游第三方故障（5xx → BLOCKED）", tc006),
    ("TC-AIQE-007", "UI Runner 自身故障（worker lost）", tc007),
    ("TC-AIQE-008", "开发修复后一键回归", tc008),
    ("TC-AIQE-009", "多端 AC 对照（能力×平台矩阵）", tc009),
    ("TC-AIQE-010", "学习候选发布（状态机）", tc010),
]


def cleanup_all() -> None:
    db = SessionLocal()
    try:
        for kind, key in reversed(CLEANUP):
            if kind == "run":
                db.execute(delete(NodeRun).where(NodeRun.run_id == key))
                db.execute(delete(TestRun).where(TestRun.id == key))
            elif kind == "workflow":
                db.execute(delete(WorkflowDefinition).where(WorkflowDefinition.id == key))
            elif kind == "node":
                db.execute(
                    delete(NodeCapabilityManifest).where(NodeCapabilityManifest.node_id == key)
                )
            elif kind == "candidate":
                db.execute(delete(LearningCandidate).where(LearningCandidate.id == key))
            elif kind == "bugpattern":
                db.execute(delete(BugPattern).where(BugPattern.pattern_key == key))
        db.commit()
    finally:
        db.close()


def main() -> int:
    for case_id, title, fn in CASES:
        run_case(case_id, title, fn)
    try:
        cleanup_all()
    except Exception as exc:  # noqa: BLE001
        RESULTS.append(
            {"id": "CLEANUP", "title": "数据清理", "status": "FAIL", "reason": str(exc)}
        )
    summary = {
        "passed": sum(1 for r in RESULTS if r["status"] == "PASS"),
        "blocked": sum(1 for r in RESULTS if r["status"] == "BLOCKED"),
        "failed": sum(1 for r in RESULTS if r["status"] == "FAIL"),
        "results": RESULTS,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
