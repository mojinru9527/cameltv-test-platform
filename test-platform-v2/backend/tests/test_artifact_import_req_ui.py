"""DSH 产物导入补齐 —— requirement / ui_case 导入分发测试。

沿用 test_ai_artifact_batch.py 的 client/auth_headers/db_session fixture 与
`_make_artifact` 模式。覆盖（计划 Task 5 用例清单）：
1. ui_case approved → 导入成功（case_type="ui"、[UI] 前缀、tags 含 UI自动化、artifact 回填）
2. ui_case title 已带 [UI] 前缀 → 不重复加前缀
3. requirement approved → 导入需求库（title/content/file_type/source_ref/creator_id 落库；
   content 为结构化 dict 时序列化为 JSON 文本留痕）
4. requirement 未审核（pending）→ 403 守卫
5. ui_case 已导入（imported）→ 重复导入拒绝
6. 跨项目产物 → 404
7. 未知 artifact_type → 业务错误拒绝
8. 批量导入混入 ui_case+requirement（治理开关开启 → 各归其库；关闭 → 403）
"""
from __future__ import annotations

import json
from unittest.mock import patch


def _make_artifact(
    db,
    *,
    artifact_id: int,
    project_id: int = 1,
    status: str = "pending",
    artifact_type: str = "test_case",
    title: str | None = None,
    content: dict | None = None,
):
    from app.models.knowledge import AiArtifact

    if content is None:
        content = {
            "title": "t", "domain": "接口测试", "module": "m", "steps": [],
            "api_method": "GET", "api_endpoint": "/x", "api_assertions": [],
        }
    row = AiArtifact(
        id=artifact_id,
        project_id=project_id,
        artifact_type=artifact_type,
        title=title or f"artifact-{artifact_id}",
        content_json=json.dumps(content, ensure_ascii=False),
        review_status=status,
    )
    db.add(row)
    db.commit()
    return row


def _import(client, auth_headers, artifact_id: int):
    return client.post(
        f"/api/v1/knowledge/ai-artifacts/{artifact_id}/import-to-test-cases",
        headers=auth_headers,
        json={"comment": ""},
    )


class TestUiCaseImport:
    def test_ui_case_import_success(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact
        from app.models.test_case import TestCase

        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="ui_case",
            title="首页冒烟",
            content={"title": "首页冒烟", "module": "首页", "priority": "P1",
                     "steps": [{"action": "打开首页"}], "expected_result": "首页正常展示"},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["artifact_id"] == 1
        assert data["ref_type"] == "test_case"
        assert data["case_id"] == data["ref_id"]  # 旧键兼容

        case = db_session.get(TestCase, data["ref_id"])
        assert case is not None
        assert case.case_type == "ui"
        assert case.title == "[UI] 首页冒烟"
        assert case.status == "draft"
        assert case.source == "ai_generated"
        assert case.case_design_method == "场景法"
        tags = json.loads(case.tags)
        assert "UI自动化" in tags
        assert "auto:dsh" in tags

        artifact = db_session.get(AiArtifact, 1)
        assert artifact.review_status == "imported"
        assert artifact.imported_ref_type == "test_case"
        assert artifact.imported_ref_id == case.id

    def test_ui_case_title_prefix_idempotent(self, client, auth_headers, db_session):
        from app.models.test_case import TestCase

        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="ui_case",
            title="[UI] 已有前缀", content={"title": "[UI] 已有前缀"},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 200, resp.text
        case = db_session.get(TestCase, resp.json()["data"]["ref_id"])
        assert case.title == "[UI] 已有前缀"  # 不重复加前缀


class TestRequirementImport:
    def test_requirement_import_success(self, client, auth_headers, db_session, admin_user):
        from app.models.knowledge import AiArtifact
        from app.models.requirement import RequirementDocument

        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="requirement",
            title="用户端 14.2.0 需求",
            content={"title": "用户端 14.2.0 需求", "content": "# 需求正文\n1. 登录"},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["artifact_id"] == 1
        assert data["ref_type"] == "requirement_document"
        assert "case_id" not in data

        doc = db_session.get(RequirementDocument, data["ref_id"])
        assert doc is not None
        assert doc.title == "用户端 14.2.0 需求"
        assert doc.content == "# 需求正文\n1. 登录"
        assert doc.file_type == "md"
        assert doc.source_ref == "dsh_artifact:1"
        assert doc.creator_id == admin_user.id  # 操作人=当前登录用户
        assert doc.project_id == 1

        artifact = db_session.get(AiArtifact, 1)
        assert artifact.review_status == "imported"
        assert artifact.imported_ref_type == "requirement_document"
        assert artifact.imported_ref_id == doc.id

    def test_requirement_content_dict_serialized(self, client, auth_headers, db_session):
        """content 为结构化 dict（非字符串）→ 序列化为 JSON 文本留痕。"""
        from app.models.requirement import RequirementDocument

        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="requirement",
            title="结构化需求",
            content={"title": "结构化需求", "content": {"modules": [{"name": "首页"}]}},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 200, resp.text
        doc = db_session.get(RequirementDocument, resp.json()["data"]["ref_id"])
        assert doc is not None
        parsed = json.loads(doc.content)
        assert parsed == {"modules": [{"name": "首页"}]}

    def test_requirement_pending_forbidden(self, client, auth_headers, db_session):
        _make_artifact(
            db_session, artifact_id=1, status="pending", artifact_type="requirement",
            content={"title": "t", "content": "# 需求"},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 403, resp.text


class TestImportGuards:
    def test_ui_case_already_imported_rejected(self, client, auth_headers, db_session):
        _make_artifact(
            db_session, artifact_id=1, status="imported", artifact_type="ui_case",
            content={"title": "x"},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 200, resp.text  # APIException(code=1) → http 200 + 业务码
        assert resp.json()["code"] == 1
        assert "已导入" in resp.json()["msg"]

    def test_cross_project_not_found(self, client, auth_headers, db_session):
        from app.models.knowledge import AiArtifact

        _make_artifact(
            db_session, artifact_id=1, project_id=999, status="approved",
            artifact_type="ui_case", content={"title": "x"},
        )
        resp = _import(client, auth_headers, 1)  # auth_headers = X-Project-Id: 1
        assert resp.status_code == 404, resp.text
        assert db_session.get(AiArtifact, 1).review_status == "approved"  # 不误改

    def test_unknown_artifact_type_rejected(self, client, auth_headers, db_session):
        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="business_rule",
            content={"title": "x"},
        )
        resp = _import(client, auth_headers, 1)
        assert resp.status_code == 200, resp.text  # APIException(code=1) → http 200 + 业务码
        assert resp.json()["code"] == 1
        assert "暂不支持导入" in resp.json()["msg"]


class TestBatchMixedImport:
    def test_batch_mixed_types_each_to_own_store(self, client, auth_headers, db_session):
        from app.core.config import settings
        from app.models.knowledge import AiArtifact
        from app.models.requirement import RequirementDocument
        from app.models.test_case import TestCase

        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="ui_case",
            title="UI用例", content={"title": "UI用例", "steps": []},
        )
        _make_artifact(
            db_session, artifact_id=2, status="approved", artifact_type="requirement",
            title="需求文档", content={"title": "需求文档", "content": "# 需求正文"},
        )
        with patch.object(settings, "ai_artifact_allow_batch_import", True):
            resp = client.post(
                "/api/v1/knowledge/ai-artifacts/batch-import",
                headers=auth_headers,
                json={"ids": [1, 2]},
            )
        assert resp.status_code == 200, resp.text
        imported = resp.json()["data"]["imported"]
        assert len(imported) == 2
        by_artifact = {item["artifact_id"]: item for item in imported}
        assert by_artifact[1]["ref_type"] == "test_case"
        assert by_artifact[2]["ref_type"] == "requirement_document"

        # 各归其库
        case = db_session.get(TestCase, by_artifact[1]["ref_id"])
        assert case is not None and case.case_type == "ui"
        doc = db_session.get(RequirementDocument, by_artifact[2]["ref_id"])
        assert doc is not None
        assert doc.file_type == "md"
        assert doc.source_ref == "dsh_artifact:2"

        assert db_session.get(AiArtifact, 1).review_status == "imported"
        assert db_session.get(AiArtifact, 2).review_status == "imported"

    def test_batch_mixed_types_flag_off_403(self, client, auth_headers, db_session):
        _make_artifact(
            db_session, artifact_id=1, status="approved", artifact_type="ui_case",
            content={"title": "x"},
        )
        _make_artifact(
            db_session, artifact_id=2, status="approved", artifact_type="requirement",
            content={"title": "y", "content": "# 需求"},
        )
        # 默认 ai_artifact_allow_batch_import=False → >1 条被治理门拒绝
        resp = client.post(
            "/api/v1/knowledge/ai-artifacts/batch-import",
            headers=auth_headers,
            json={"ids": [1, 2]},
        )
        assert resp.status_code == 403, resp.text
