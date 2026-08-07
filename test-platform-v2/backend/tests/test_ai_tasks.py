"""Batch 116（C102-1）— AI 异步任务基建与端点测试（mock AI 服务）。"""
from __future__ import annotations

import time
from unittest.mock import patch

from app.services import ai_tasks


def test_submit_and_complete_task() -> None:
    def job():
        return {"ok": True, "cases": 3}

    task = ai_tasks.submit_ai_task(job, task_type="generate", project_id=1)
    for _ in range(50):
        t = ai_tasks.get_ai_task(task["id"])
        if t["status"] == "done":
            break
        time.sleep(0.02)
    assert t["status"] == "done"
    assert t["result"] == {"ok": True, "cases": 3}


def test_submit_task_error() -> None:
    def bad():
        raise ValueError("boom")

    task = ai_tasks.submit_ai_task(bad, task_type="extract", project_id=1)
    for _ in range(50):
        t = ai_tasks.get_ai_task(task["id"])
        if t["status"] != "running":
            break
        time.sleep(0.02)
    assert t["status"] == "failed"
    assert "boom" in t["error"]


def test_generate_async_endpoint(client, auth_headers, db_session) -> None:
    from app.models.requirement import RequirementDocument
    doc = RequirementDocument(project_id=1, title="doc", content="大文档内容", file_type="md")
    db_session.add(doc)
    db_session.flush()
    client.headers.update(auth_headers)
    fake = {"id": "ai-test", "status": "running", "type": "generate", "result": None, "error": ""}
    with patch("app.services.ai_tasks.submit_ai_task", return_value=fake) as m:
        r = client.post(f"/api/v1/requirements/{doc.id}/generate-async")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["id"] == "ai-test"
    m.assert_called_once()


def test_ai_task_status_404(client, auth_headers) -> None:
    client.headers.update(auth_headers)
    with patch("app.services.ai_tasks.get_ai_task", return_value=None):
        r = client.get("/api/v1/requirements/ai-task/nope")
    assert r.status_code == 404