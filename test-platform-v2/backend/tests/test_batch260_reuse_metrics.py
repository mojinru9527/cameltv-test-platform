"""Batch 260 / B3-4 — 复用建议命中率埋点与聚合。

DoD（backlog B3-4）：命中率可统计；≥50% 目标进入 B4 验收。
约束（PRD §3）：**不改既有** `get_reuse_suggestions` / `GET /version-tasks/knowledge/reuse` 的契约，
本批只旁挂埋点——用断言守住这一点。
"""
from __future__ import annotations

import inspect

import pytest

from app.core.exceptions import APIException
from app.models.reuse_suggestion import ReuseSuggestionEvent
from app.services import reuse_metrics_service, version_task_service


class TestRecording:
    def test_records_suggestion_then_decision(self, db_session):
        reuse_metrics_service.record_suggestion(
            db_session, project_id=1, task_id=10, suggestion_ref="rec:5", title="上一版覆盖的体育模块"
        )
        reuse_metrics_service.record_decision(
            db_session, project_id=1, task_id=10, suggestion_ref="rec:5", decision="adopted", decided_by=7
        )
        stats = reuse_metrics_service.reuse_stats(db_session, project_id=1)
        assert stats["suggested"] == 1
        assert stats["adopted"] == 1
        assert stats["hit_rate"] == 1.0
        assert stats["meets_50pct"] is True

    def test_duplicate_recording_is_idempotent(self, db_session):
        for _ in range(3):
            reuse_metrics_service.record_suggestion(
                db_session, project_id=1, task_id=10, suggestion_ref="rec:5"
            )
        assert db_session.query(ReuseSuggestionEvent).count() == 1
        assert reuse_metrics_service.reuse_stats(db_session, project_id=1)["suggested"] == 1

    def test_decision_must_be_adopted_or_rejected(self, db_session):
        reuse_metrics_service.record_suggestion(
            db_session, project_id=1, task_id=10, suggestion_ref="rec:5"
        )
        with pytest.raises(APIException):
            reuse_metrics_service.record_decision(
                db_session, project_id=1, task_id=10, suggestion_ref="rec:5", decision="maybe"
            )

    def test_empty_ref_is_rejected(self, db_session):
        with pytest.raises(APIException):
            reuse_metrics_service.record_suggestion(
                db_session, project_id=1, task_id=10, suggestion_ref="  "
            )


class TestHitRate:
    def test_hit_rate_is_adopted_over_suggested(self, db_session):
        # 4 条建议：2 采纳、1 否掉、1 待定 → 命中率 2/4 = 50%
        for index in range(4):
            reuse_metrics_service.record_suggestion(
                db_session, project_id=1, task_id=20, suggestion_ref=f"rec:{index}"
            )
        reuse_metrics_service.record_decision(
            db_session, project_id=1, task_id=20, suggestion_ref="rec:0", decision="adopted"
        )
        reuse_metrics_service.record_decision(
            db_session, project_id=1, task_id=20, suggestion_ref="rec:1", decision="adopted"
        )
        reuse_metrics_service.record_decision(
            db_session, project_id=1, task_id=20, suggestion_ref="rec:2", decision="rejected"
        )
        stats = reuse_metrics_service.reuse_stats(db_session, project_id=1)
        assert stats == {
            "suggested": 4,
            "adopted": 2,
            "rejected": 1,
            "hit_rate": 0.5,
            "meets_50pct": True,
            "pending": 1,
        }

    def test_below_threshold_is_reported_honestly(self, db_session):
        for index in range(4):
            reuse_metrics_service.record_suggestion(
                db_session, project_id=1, task_id=21, suggestion_ref=f"rec:{index}"
            )
        reuse_metrics_service.record_decision(
            db_session, project_id=1, task_id=21, suggestion_ref="rec:0", decision="adopted"
        )
        stats = reuse_metrics_service.reuse_stats(db_session, project_id=1)
        assert stats["hit_rate"] == 0.25
        assert stats["meets_50pct"] is False

    def test_no_suggestions_yields_none_not_false(self, db_session):
        """没有数据时不能报"未达标"，也不能报"达标"——必须是未知。"""
        stats = reuse_metrics_service.reuse_stats(db_session, project_id=1)
        assert stats["suggested"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["meets_50pct"] is None

    def test_project_isolation(self, db_session):
        reuse_metrics_service.record_suggestion(
            db_session, project_id=1, task_id=1, suggestion_ref="rec:1"
        )
        reuse_metrics_service.record_suggestion(
            db_session, project_id=2, task_id=2, suggestion_ref="rec:2"
        )
        assert reuse_metrics_service.reuse_stats(db_session, project_id=1)["suggested"] == 1
        assert reuse_metrics_service.reuse_stats(db_session, project_id=2)["suggested"] == 1
        assert reuse_metrics_service.reuse_stats(db_session, project_id=3)["suggested"] == 0


class TestExistingContractUnchanged:
    def test_get_reuse_suggestions_signature_is_unchanged(self):
        """B12 与前端依赖既有返回契约；本批只旁挂埋点，不得改签名/返回形状。"""
        signature = inspect.signature(version_task_service.get_reuse_suggestions)
        assert list(signature.parameters) == ["db", "project_id", "limit"]
        assert signature.parameters["limit"].default == 5

    def test_api_endpoints(self, db_session, client, auth_headers):
        # Batch 268（C268-2）：决策必须对应**已带出**的建议，否则命中率会 >1。
        # 因此这里先落一条 suggested 事件，再走 API 记采纳。
        reuse_metrics_service.record_suggestion(
            db_session, project_id=1, task_id=5, suggestion_ref="rec:api", title="上一版覆盖的体育模块"
        )
        created = client.post(
            "/api/v1/version-tasks/knowledge/reuse-decisions",
            json={"task_id": 5, "suggestion_ref": "rec:api", "decision": "adopted"},
            headers=auth_headers,
        )
        assert created.status_code == 200
        assert created.json()["data"]["decision"] == "adopted"

        stats = client.get("/api/v1/version-tasks/knowledge/reuse-stats", headers=auth_headers)
        assert stats.status_code == 200
        assert stats.json()["data"]["adopted"] == 1

    def test_api_rejects_invalid_decision(self, client, auth_headers):
        resp = client.post(
            "/api/v1/version-tasks/knowledge/reuse-decisions",
            json={"task_id": 5, "suggestion_ref": "rec:api", "decision": "maybe"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # schema 层就拦住
