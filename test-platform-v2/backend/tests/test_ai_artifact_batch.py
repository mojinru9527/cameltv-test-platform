"""Batch 94 — AI 产物批量审核/采纳/导入端点测试。

覆盖：
- 批量采纳/驳回（pending → approved/rejected，去重，missing 归集）
- 批量导入（治理开关 ai_artifact_allow_batch_import 门控；>1 条关闭时 403）
- 项目隔离（跨项目产物 → missing/404，不误改）
- 静态路径优先（/ai-artifacts/batch-* 不被 {artifact_id} 遮蔽 → 422 回归防护）
"""
from __future__ import annotations

from unittest.mock import patch


def _make_artifact(db, *, artifact_id: int, project_id: int = 1, status: str = "pending"):
    from app.models.knowledge import AiArtifact

    row = AiArtifact(
        id=artifact_id,
        project_id=project_id,
        artifact_type="test_case",
        title=f"artifact-{artifact_id}",
        content_json='{"title":"t","domain":"接口测试","module":"m","steps":[],"api_method":"GET","api_endpoint":"/x","api_assertions":[]}',
        review_status=status,
    )
    db.add(row)
    db.commit()
    return row


class TestBatchApprove:
    def test_approve_multiple_pending(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact

        _make_artifact(db_session, artifact_id=1)
        _make_artifact(db_session, artifact_id=2)

        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-approve",
            headers=auth_headers,
            json={"ids": [1, 2], "comment": "batch approve"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["approved"] == [1, 2]
        assert data["missing"] == []
        assert db_session.get(AiArtifact, 1).review_status == "approved"
        assert db_session.get(AiArtifact, 2).review_status == "approved"

    def test_approve_dedup_and_missing(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact

        _make_artifact(db_session, artifact_id=1)
        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-approve",
            headers=auth_headers,
            json={"ids": [1, 1, 999]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["approved"] == [1]
        assert data["missing"] == [999]

    def test_cross_project_not_modified(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact

        _make_artifact(db_session, artifact_id=1, project_id=999, status="pending")
        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-approve",
            headers=auth_headers,  # X-Project-Id: 1
            json={"ids": [1]},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["missing"] == [1]
        assert db_session.get(AiArtifact, 1).review_status == "pending"


class TestBatchReject:
    def test_reject_multiple(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact

        _make_artifact(db_session, artifact_id=1)
        _make_artifact(db_session, artifact_id=2)
        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-reject",
            headers=auth_headers,
            json={"ids": [1, 2], "comment": "缺字段"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["rejected"] == [1, 2]
        assert db_session.get(AiArtifact, 1).review_status == "rejected"
        assert db_session.get(AiArtifact, 2).review_status == "rejected"


class TestBatchImport:
    def test_import_requires_governance_flag(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact

        _make_artifact(db_session, artifact_id=1, status="approved")
        _make_artifact(db_session, artifact_id=2, status="approved")
        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-import",
            headers=auth_headers,
            json={"ids": [1, 2]},
        )
        # 默认 ai_artifact_allow_batch_import=False → 批量导入被治理门拒绝
        assert resp.status_code == 403, resp.text

    def test_import_approved_when_flag_enabled(self, client, auth_headers, db_session):
        from app.core.config import settings
        from app.models.knowledge import AiArtifact

        _make_artifact(db_session, artifact_id=1, status="approved")
        _make_artifact(db_session, artifact_id=2, status="approved")
        with patch.object(settings, "ai_artifact_allow_batch_import", True):
            resp = client.post(
                "/api/v1/knowledge/ai-artifacts/batch-import",
                headers=auth_headers,
                json={"ids": [1, 2]},
            )
        assert resp.status_code == 200, resp.text
        imported = resp.json()["data"]["imported"]
        assert len(imported) == 2
        assert db_session.get(AiArtifact, 1).review_status == "imported"
        assert db_session.get(AiArtifact, 2).review_status == "imported"


class TestRouteOrder:
    def test_batch_routes_not_shadowed_by_param_route(self, client, auth_headers, db_session):
        """/ai-artifacts/batch-approve 必须注册在 {artifact_id} 之前（422 回归防护）。"""
        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-approve",
            headers=auth_headers,
            json={"ids": []},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"] == {"approved": [], "missing": []}
