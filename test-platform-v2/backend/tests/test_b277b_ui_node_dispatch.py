"""batch-277b / P0-4：/uitest 节点派发（dispatch/sync）+ 节点 spec 执行器。

覆盖：
- build_payload：读 spec、静态安全拦截、环境变量注入、路径越权拒绝；
- dispatch：创建 ExecutionJob(kind="ui") 并绑定 run；
- sync_run_from_job：状态/结果/证据目录投影 + 幂等；
- execution_job_service.report：上报后自动投影（P0-4 的衔接点）；
- 节点 run_spec_files：报告解析、非法文件名、超时、无报告。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models.execution_job import ExecutionJob
from app.models.ui_test import UiTestJob, UiTestRun
from app.services import execution_job_service, ui_job_dispatch

REPO_ROOT = Path(__file__).resolve().parents[3]
NODE_EXECUTOR = REPO_ROOT / "scripts" / "node" / "cameltv_node" / "executor.py"


def _load_node_executor():
    spec = importlib.util.spec_from_file_location("cameltv_node_executor_b277b", NODE_EXECUTOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _mk_job(db, *, spec: str = "ok.spec.ts") -> UiTestJob:
    job = UiTestJob(project_id=1, name="ui", test_spec=spec, browser="chromium")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _mk_run(db, job: UiTestJob) -> UiTestRun:
    run = UiTestRun(job_id=job.id, status="pending", base_url="http://example.test")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@pytest.fixture()
def spec_dir(tmp_path, monkeypatch):
    from app.services import playwright_executor as pw

    directory = tmp_path / "playwright"
    directory.mkdir()
    monkeypatch.setattr(pw, "_runner_dir", lambda: directory)
    monkeypatch.setattr(pw, "_resolve_environment_variables", lambda db, env_id: {"FOO": "bar"})
    return directory


@pytest.fixture()
def node_executor(monkeypatch):
    """加载节点执行器，并禁用仓库内 playwright root（单测写临时目录，不污染仓库）。"""
    module = _load_node_executor()
    monkeypatch.setattr(module, "_playwright_root", lambda: None)
    return module


def test_build_payload_reads_spec_and_env(db_session, spec_dir):
    (spec_dir / "ok.spec.ts").write_text("test('ok', async () => {});", encoding="utf-8")
    job = _mk_job(db_session)
    payload = ui_job_dispatch.build_payload(
        db_session, job, project_id=1, base_url="http://example.test"
    )
    assert payload["mode"] == "spec"
    assert payload["entry"] == "ok.spec.ts"
    assert payload["files"] == [{"name": "ok.spec.ts", "content": "test('ok', async () => {});"}]
    assert payload["env"] == {"FOO": "bar"}
    assert payload["base_url"] == "http://example.test"
    assert payload["browser"] == "chromium"


def test_build_payload_rejects_unsafe_spec(db_session, spec_dir):
    (spec_dir / "bad.spec.ts").write_text(
        "const cp = require('child_process');", encoding="utf-8"
    )
    job = _mk_job(db_session, spec="bad.spec.ts")
    with pytest.raises(ValueError, match="禁止"):
        ui_job_dispatch.build_payload(db_session, job, project_id=1, base_url="")


def test_build_payload_rejects_path_traversal(db_session, spec_dir):
    job = _mk_job(db_session, spec="../outside.spec.ts")
    with pytest.raises(ValueError, match="测试脚本不存在"):
        ui_job_dispatch.build_payload(db_session, job, project_id=1, base_url="")


def test_dispatch_creates_ui_job_and_links_run(db_session):
    job = _mk_job(db_session)
    run = _mk_run(db_session, job)
    exec_job = ui_job_dispatch.dispatch(
        db_session, job, run, project_id=1, payload={"mode": "spec", "entry": "ok.spec.ts"}
    )
    assert exec_job.kind == "ui"
    assert exec_job.project_id == 1
    assert json.loads(exec_job.payload_json)["mode"] == "spec"
    db_session.refresh(run)
    assert run.execution_job_id == exec_job.id


def test_sync_run_maps_status_result_and_evidence(db_session):
    job = _mk_job(db_session)
    run = _mk_run(db_session, job)
    exec_job = ui_job_dispatch.dispatch(db_session, job, run, project_id=1, payload={})
    exec_job.status = "completed"
    exec_job.attempt = 1
    exec_job.result_json = json.dumps({"total": 1, "passed": 1})
    exec_job.finished_at = datetime.now(timezone.utc)
    db_session.commit()

    synced = ui_job_dispatch.sync_run_from_job(db_session, exec_job)
    assert synced is not None
    assert synced.status == "done"
    assert json.loads(synced.result)["passed"] == 1
    assert f"job-{exec_job.id}" in synced.artifact_dir
    db_session.refresh(job)
    assert job.status == "done"


def test_sync_run_is_idempotent(db_session):
    job = _mk_job(db_session)
    run = _mk_run(db_session, job)
    exec_job = ui_job_dispatch.dispatch(db_session, job, run, project_id=1, payload={})
    exec_job.status = "failed"
    exec_job.error_message = "boom"
    db_session.commit()
    first = ui_job_dispatch.sync_run_from_job(db_session, exec_job)
    second = ui_job_dispatch.sync_run_from_job(db_session, exec_job)
    assert first.status == second.status == "fail"
    assert second.error_message == "boom"


def test_report_hook_syncs_linked_run(db_session):
    job = _mk_job(db_session)
    run = _mk_run(db_session, job)
    exec_job = ui_job_dispatch.dispatch(db_session, job, run, project_id=1, payload={})
    exec_job.status = "running"
    exec_job.node_id = "node-1"
    db_session.commit()

    updated = execution_job_service.report(
        db_session,
        job_id=exec_job.id,
        node_id="node-1",
        status="completed",
        summary="1/1 pass",
        result={"total": 1, "passed": 1},
    )
    assert updated is not None and updated.status == "completed"
    db_session.refresh(run)
    assert run.status == "done"
    assert run.finished_at is not None


def test_node_run_spec_files_parses_report(node_executor, tmp_path):
    executor = node_executor

    def fake_runner(cmd, *, cwd, env, timeout):
        report = Path(env["PLAYWRIGHT_JSON_OUTPUT_NAME"])
        report.write_text(
            json.dumps(
                {
                    "suites": [
                        {
                            "specs": [
                                {"title": "a", "tests": [{"results": [{"status": "passed"}]}]},
                                {"title": "b", "tests": [{"results": [{"status": "failed"}]}]},
                            ]
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return 1, "stdout", "stderr"

    result = executor.run_spec_files(
        [{"name": "a.spec.ts", "content": "test('a', async () => {});"}],
        entry="a.spec.ts",
        evidence_dir=tmp_path,
        base_url="http://example.test",
        runner=fake_runner,
    )
    assert result["total"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["all_pass"] is False
    assert {c["name"] for c in result["cases"]} == {"a", "b"}


def test_node_run_spec_files_rejects_unsafe_name(node_executor, tmp_path):
    executor = node_executor
    result = executor.run_spec_files(
        [{"name": "../evil.spec.ts", "content": "x"}],
        entry="../evil.spec.ts",
        evidence_dir=tmp_path,
    )
    assert result["all_pass"] is False
    assert "非法 spec 文件名" in result["error"]


def test_node_run_spec_files_timeout(node_executor, tmp_path):
    executor = node_executor

    def timeout_runner(cmd, *, cwd, env, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    result = executor.run_spec_files(
        [{"name": "a.spec.ts", "content": "x"}],
        entry="a.spec.ts",
        evidence_dir=tmp_path,
        runner=timeout_runner,
    )
    assert result["all_pass"] is False
    assert "超时" in result["error"]


def test_node_run_spec_files_without_report(node_executor, tmp_path):
    executor = node_executor

    def no_report_runner(cmd, *, cwd, env, timeout):
        return 2, "", "npx: command failed"

    result = executor.run_spec_files(
        [{"name": "a.spec.ts", "content": "x"}],
        entry="a.spec.ts",
        evidence_dir=tmp_path,
        runner=no_report_runner,
    )
    assert result["all_pass"] is False
    assert "未生成 Playwright JSON 报告" in result["error"]

def test_trigger_job_node_mode_dispatches(db_session, spec_dir, monkeypatch):
    from app.core.config import settings
    from app.services import ui_test_service

    (spec_dir / "ok.spec.ts").write_text("test('ok', async () => {});", encoding="utf-8")
    job = _mk_job(db_session)
    monkeypatch.setattr(settings, "uitest_execution_mode", "node")

    result = ui_test_service.trigger_job(db_session, job.id, 1)
    run = db_session.get(UiTestRun, result["id"])
    assert run is not None
    assert run.execution_job_id is not None
    exec_job = db_session.get(ExecutionJob, run.execution_job_id)
    assert exec_job.kind == "ui"
    assert json.loads(exec_job.payload_json)["entry"] == "ok.spec.ts"
    db_session.refresh(job)
    assert job.status == "running"
