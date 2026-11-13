"""TC-AIQE-003 / TC-AIQE-008 阻塞项验证（隔离 Test 实例，真实 HTTP + 服务层）。

运行（Test backend 容器内）：
  docker exec -e PYTHONPATH=/app -w /app aiqe-test-backend python /tmp/tc_aiqe_unblocked_verify.py
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import delete, select

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services import dag_scheduler
from app.core.db import SessionLocal
from app.models.defect import Defect, DefectRegression
from app.models.project import Project

BASE = "http://127.0.0.1:8000"
RESULTS: list[dict] = []
CLEANUP: list[tuple[str, object]] = []

GRAPH = {
    "schema_version": "1.0",
    "retry": {"max_attempts": 2},
    "nodes": [{"key": "api", "driver": "http"}],
    "edges": [],
}


def client() -> httpx.Client:
    pw = os.environ.get("ADMIN_PASSWORD", "")
    c = httpx.Client(base_url=BASE, timeout=30, trust_env=False)
    login = c.post("/api/v1/auth/login", json={"username": "admin", "password": pw})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def project_id(db) -> int:
    pid = db.scalar(select(Project.id).order_by(Project.id))
    if pid is None:
        raise RuntimeError("Test 库无项目")
    return int(pid)


def tc003(c: httpx.Client) -> dict:
    db = SessionLocal()
    try:
        pid = project_id(db)
        run = TestRun(
            project_id=pid,
            run_key=f"TC003-{uuid.uuid4().hex[:8]}",
            source_type="manual",
            status="QUEUED",
        )
        db.add(run)
        db.flush()
        CLEANUP.append(("run", run.id))
        dag_scheduler.create_node_runs(db, run.id, GRAPH)
        dag_scheduler.schedule(db, run.id, GRAPH)
        dag_scheduler.mark_running(db, run.id, "api")
        dag_scheduler.complete_node(
            db, run.id, "api", "FAILED", GRAPH, error_class="HTTP_503"
        )
        db.commit()
        db.refresh(run)
        first_failed_kept = run.status == "RUNNING"
        dag_scheduler.schedule(db, run.id, GRAPH)
        dag_scheduler.mark_running(db, run.id, "api")
        dag_scheduler.complete_node(db, run.id, "api", "PASSED", GRAPH)
        db.commit()
        db.refresh(run)
        attempts = [
            row.status
            for row in db.scalars(
                select(StepAttempt)
                .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
                .where(NodeRun.run_id == run.id)
                .order_by(StepAttempt.attempt_no)
            )
        ]
        resp = c.get(
            f"/api/v1/aiqe/runs/{run.id}/attempts",
            headers={"X-Project-Id": str(pid)},
        )
        api_attempts = [a["status"] for a in resp.json()["data"]["items"][0]["attempts"]]
        assert first_failed_kept, "首次失败后 Run 不应仍在 RUNNING"
        assert attempts == ["FAILED", "PASSED"], attempts
        assert api_attempts == ["FAILED", "PASSED"], api_attempts
        assert run.outcome == "PASS"
        return {"run": run.run_key, "attempts": attempts, "api": api_attempts}
    finally:
        db.close()


def tc008(c: httpx.Client) -> dict:
    db = SessionLocal()
    try:
        pid = project_id(db)
        defect_resp = c.post(
            "/api/v1/defects",
            headers={"X-Project-Id": str(pid)},
            json={"title": f"TC008 回归缺陷 {uuid.uuid4().hex[:6]}", "severity": "P1"},
        )
        defect_resp.raise_for_status()
        defect_id = defect_resp.json()["data"]["id"]
        CLEANUP.append(("defect", defect_id))

        old = TestRun(
            project_id=pid,
            run_key=f"OLD-{uuid.uuid4().hex[:8]}",
            source_type="manual",
            status="COMPLETED",
            outcome="FAIL",
        )
        db.add(old)
        db.commit()
        CLEANUP.append(("run", old.id))

        reg_resp = c.post(
            "/api/v1/aiqe/regressions",
            headers={"X-Project-Id": str(pid)},
            json={
                "defect_id": defect_id,
                "fixed_sha": "abc1234def",
                "previous_run_id": old.id,
            },
        )
        reg_resp.raise_for_status()
        data = reg_resp.json()["data"]
        CLEANUP.append(("regression", data["id"]))

        db.expire_all()
        old_after = db.get(TestRun, old.id)
        assert old_after.status == "COMPLETED" and old_after.outcome == "FAIL"
        detail = c.get(
            f"/api/v1/aiqe/regressions/{data['id']}",
            headers={"X-Project-Id": str(pid)},
        )
        assert detail.status_code == 200
        assert data["run"]["status"] == "QUEUED"
        assert data["run"]["commit_sha"] == "abc1234def"
        assert data["run"]["retest_of"] == old.id
        return {
            "regression_id": data["id"],
            "verification_run": data["run"]["run_key"],
            "old_run_untouched": True,
        }
    finally:
        db.close()


def cleanup_all() -> None:
    db = SessionLocal()
    try:
        for kind, key in reversed(CLEANUP):
            if kind == "run":
                db.execute(delete(StepAttempt).where(StepAttempt.node_run_id.in_(
                    select(NodeRun.id).where(NodeRun.run_id == key)
                )))
                db.execute(delete(NodeRun).where(NodeRun.run_id == key))
                db.execute(delete(TestRun).where(TestRun.id == key))
            elif kind == "regression":
                db.execute(delete(DefectRegression).where(DefectRegression.id == key))
            elif kind == "defect":
                db.execute(delete(Defect).where(Defect.id == key))
        db.commit()
    finally:
        db.close()


def main() -> int:
    c = client()
    for name, fn in (("TC-AIQE-003", tc003), ("TC-AIQE-008", tc008)):
        try:
            RESULTS.append({"id": name, "status": "PASS", "detail": fn(c)})
        except Exception as exc:  # noqa: BLE001
            RESULTS.append(
                {"id": name, "status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}
            )
    try:
        cleanup_all()
    except Exception as exc:  # noqa: BLE001
        RESULTS.append({"id": "CLEANUP", "status": "FAIL", "reason": str(exc)})
    print(json.dumps({"results": RESULTS}, ensure_ascii=False, indent=2, default=str))
    return 0 if all(r["status"] == "PASS" for r in RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
