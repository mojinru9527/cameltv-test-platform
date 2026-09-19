"""Batch 268 / C267-3 — 复用命中率**埋点接线**。

此前 `reuse_metrics_service.record_suggestion` 只有定义、没有调用点：
- Batch 260 的测试只测了"记录 + 聚合"本身，没有测"谁在什么时候记录"；
- 生产实证 `reuse_suggestion_event` 0 行（同期 6 个版本任务），命中率 `adopted/suggested` 恒为 0。

本批把"建任务时带出上版建议"这一时刻接上埋点，并用测试守住——否则 ⑦ 的复用率永远测不出。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from app.models.reuse_suggestion import ReuseSuggestionEvent
from app.models.version_knowledge import VersionKnowledgeRecord
from app.services import reuse_metrics_service, version_task_service

BACKEND = Path(__file__).resolve().parents[1]
DRIVER = BACKEND / "scripts" / "drill_three_versions.py"


def _load_driver():
    spec = importlib.util.spec_from_file_location("drill_three_versions_reuse", DRIVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_knowledge(db, project_id: int = 1, version: str = "16.1") -> VersionKnowledgeRecord:
    task = version_task_service.create_task(
        db, project_id=project_id, title=f"试点 {version}", version=version
    )
    record = VersionKnowledgeRecord(
        project_id=project_id,
        task_id=task.id,
        version=version,
        title=f"试点 {version} 知识记录",
        verdict="pass",
        coverage=json.dumps({"pass": 8, "fail": 2}),
        plan_summary=json.dumps(
            [{"title": "登录冒烟", "status": "adopted"}, {"title": "赛事列表", "status": "modified"}]
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_create_task_records_suggested_events(db_session):
    _seed_knowledge(db_session, version="16.1")
    db_session.query(ReuseSuggestionEvent).delete()
    db_session.commit()

    version_task_service.create_task(db_session, project_id=1, title="试点 16.2", version="16.2")

    events = db_session.query(ReuseSuggestionEvent).all()
    assert len(events) == 2, "建任务时应按**建议条目**记录事件"
    assert {event.decision for event in events} == {"suggested"}
    assert {event.title for event in events} == {"登录冒烟", "赛事列表"}
    stats = reuse_metrics_service.reuse_stats(db_session, project_id=1)
    assert stats["suggested"] == 2


def test_hit_rate_measurable_after_decision(db_session):
    _seed_knowledge(db_session, version="16.1")
    db_session.query(ReuseSuggestionEvent).delete()
    db_session.commit()

    task = version_task_service.create_task(db_session, project_id=1, title="试点 16.2", version="16.2")
    event = db_session.query(ReuseSuggestionEvent).first()
    reuse_metrics_service.record_decision(
        db_session,
        project_id=1,
        task_id=task.id,
        suggestion_ref=event.suggestion_ref,
        decision="adopted",
        decided_by=7,
    )
    stats = reuse_metrics_service.reuse_stats(db_session, project_id=1)
    assert stats["suggested"] == 2 and stats["adopted"] == 1
    assert stats["hit_rate"] == 0.5
    assert stats["meets_50pct"] is True


def test_no_previous_knowledge_means_no_suggestion_events(db_session):
    db_session.query(ReuseSuggestionEvent).delete()
    db_session.commit()
    version_task_service.create_task(db_session, project_id=99, title="空项目", version="1.0")
    assert db_session.query(ReuseSuggestionEvent).count() == 0


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, response):
        self._response = response
        self.paths: list[str] = []

    def get(self, path, headers=None):
        self.paths.append(path)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def test_driver_reads_platform_reuse_stats():
    import httpx

    driver = _load_driver()
    client = _FakeClient(_FakeResponse(200, {"data": {"suggested": 6, "adopted": 4, "hit_rate": 0.6667}}))
    assert driver._platform_reuse_stats(client, {}) == (6, 4)
    assert client.paths == ["/api/v1/version-tasks/knowledge/reuse-stats"]

    fallback = _FakeClient(_FakeResponse(500, {}))
    assert driver._platform_reuse_stats(fallback, {}) == (0, 0)
    assert driver._platform_reuse_stats(_FakeClient(httpx.ReadError("boom")), {}) == (0, 0)
