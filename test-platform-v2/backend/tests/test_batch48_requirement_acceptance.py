"""Batch 48 requirement-service acceptance regressions.

These tests reproduce the production-path defects found by Batch 47.  They
intentionally exercise route behaviour and committed database state instead
of only checking schemas or mocked transaction entry points.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.api_asset import ApiEndpoint, ApiService
from app.models.audit import AuditLog
from app.models.defect import Defect
from app.models.requirement import RequirementDocument
from app.models.requirement_review import RequirementReview
from app.models.test_case import TestCase as CaseModel
from app.models.test_plan import (
    TestExecution as ExecutionModel,
    TestPlan as PlanModel,
    TestPlanCase as PlanCaseModel,
)
from app.schemas.requirement import (
    AIGeneratedCase,
    TestFunctionPoint as FunctionPointSchema,
)
from app.services import audit_service, requirement_service, test_case_service


def _add_document(
    db_session,
    *,
    project_id: int = 1,
    title: str = "Batch48 requirement",
    ai_raw: dict | None = None,
    extraction_raw: dict | None = None,
) -> RequirementDocument:
    row = RequirementDocument(
        project_id=project_id,
        creator_id=1,
        title=title,
        file_type="md",
        source_ref=f"{title}.md",
        content="# requirement",
        ai_raw=json.dumps(ai_raw or {}, ensure_ascii=False) if ai_raw is not None else "",
        extraction_raw=(
            json.dumps(extraction_raw or {}, ensure_ascii=False)
            if extraction_raw is not None
            else ""
        ),
        extraction_status="confirmed" if extraction_raw is not None else "not_started",
        status="generated" if ai_raw is not None else "parsed",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _generated_payload(title: str = "original case") -> dict:
    return {
        "functional_cases": [
            {
                "title": title,
                "priority": "P0",
                "domain": "需求服务",
                "module": "导入",
                "preconditions": "存在 AI 结果",
                "steps": [{"step": 1, "desc": "执行", "expected": "成功"}],
                "expected_result": "original result",
            }
        ],
        "api_cases": [
            {
                "title": "api case",
                "priority": "P1",
                "domain": "接口测试",
                "module": "导入",
                "steps": [],
                "expected_result": "HTTP 200",
                "api_method": "GET",
                "api_endpoint": "/api/demo",
            }
        ],
        "requirement_analysis": {
            "extracted_requirements": [],
            "overall_assessment": "assessment",
        },
    }


def test_requirement_detail_returns_full_content_and_is_project_scoped(
    client, auth_headers, db_session
):
    own = _add_document(db_session, title="own detail")
    foreign = _add_document(db_session, project_id=2, title="foreign detail")

    response = client.get(f"/api/v1/requirements/{own.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["content"] == "# requirement"

    foreign_response = client.get(
        f"/api/v1/requirements/{foreign.id}", headers=auth_headers
    )
    assert foreign_response.status_code == 404
    assert "foreign detail" not in foreign_response.text


def test_requirement_list_server_paginates_searches_and_returns_creator(
    client, auth_headers, db_session, admin_user,
):
    rows = [
        RequirementDocument(
            project_id=1,
            creator_id=admin_user.id,
            title="only-on-page-2",
            file_type="md",
            source_ref="target.md",
            content="must not appear in list response",
            status="parsed",
        )
    ]
    rows.extend(
        RequirementDocument(
            project_id=1,
            creator_id=admin_user.id,
            title=f"document-{index:03d}",
            file_type="md",
            source_ref=f"document-{index:03d}.md",
            content="large body",
            status="parsed",
        )
        for index in range(100)
    )
    db_session.add_all(rows)
    db_session.add(
        RequirementDocument(
            project_id=2,
            creator_id=admin_user.id,
            title="foreign document",
            file_type="md",
            source_ref="foreign.md",
            content="secret",
            status="parsed",
        )
    )
    db_session.commit()

    first = client.get(
        "/api/v1/requirements",
        headers=auth_headers,
        params={"page": 1, "page_size": 100},
    )
    second = client.get(
        "/api/v1/requirements",
        headers=auth_headers,
        params={"page": 2, "page_size": 100},
    )
    search = client.get(
        "/api/v1/requirements",
        headers=auth_headers,
        params={"keyword": "only-on-page-2"},
    )

    assert first.status_code == second.status_code == search.status_code == 200
    assert first.json()["data"]["total"] == second.json()["data"]["total"] == 101
    assert len(first.json()["data"]["items"]) == 100
    assert [item["title"] for item in second.json()["data"]["items"]] == [
        "only-on-page-2"
    ]
    assert search.json()["data"]["total"] == 1
    target = search.json()["data"]["items"][0]
    assert target["title"] == "only-on-page-2"
    assert target["creator_name"] == "admin_test"
    assert "content" not in target


def test_upload_20mb_plus_one_returns_413_without_database_or_audit_side_effects(
    client, auth_headers, db_session
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers=auth_headers,
        files={"file": ("too-large.md", b"x" * (20 * 1024 * 1024 + 1), "text/markdown")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == 413
    assert db_session.scalar(select(func.count(RequirementDocument.id))) == 0
    assert db_session.scalar(select(func.count(AuditLog.id))) == 0


def test_upload_exactly_20mb_is_not_rejected_as_multipart_overhead(
    client, auth_headers
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers=auth_headers,
        files={"file": ("at-limit.md", b"x" * (20 * 1024 * 1024), "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_upload_20mb_minus_one_is_accepted(
    client, auth_headers
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers=auth_headers,
        files={
            "file": (
                "under-limit.md",
                b"x" * (20 * 1024 * 1024 - 1),
                "text/markdown",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_forged_small_content_length_cannot_bypass_actual_upload_limit(
    client, auth_headers, db_session
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers={**auth_headers, "Content-Length": "1"},
        files={
            "file": (
                "forged-length.md",
                b"x" * (20 * 1024 * 1024 + 1),
                "text/markdown",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == 413
    assert db_session.scalar(select(func.count(RequirementDocument.id))) == 0
    assert db_session.scalar(select(func.count(AuditLog.id))) == 0


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("unsupported.txt", b"plain text is not an accepted requirement format"),
        ("empty.md", b""),
        ("broken.docx", b"not-a-zip"),
        ("broken.xlsx", b"not-an-excel-workbook"),
    ],
)
def test_invalid_requirement_upload_returns_400_without_side_effects(
    client, auth_headers, db_session, filename, content
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers=auth_headers,
        files={"file": (filename, content, "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["msg"]
    assert db_session.scalar(select(func.count(RequirementDocument.id))) == 0
    assert db_session.scalar(select(func.count(AuditLog.id))) == 0


def test_requirement_upload_and_audit_are_committed_together(
    client, auth_headers, db_session
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers=auth_headers,
        files={"file": ("atomic-audit.md", b"# atomic", "text/markdown")},
    )
    assert response.status_code == 200

    # Simulate request-session close: any flush-only audit row would disappear.
    db_session.rollback()
    assert db_session.scalar(select(func.count(RequirementDocument.id))) == 1
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "requirement:upload"
        )
    ) == 1


def test_audit_failure_rolls_back_requirement_upload(
    client, auth_headers, db_session, monkeypatch
):
    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(audit_service, "write_audit", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/v1/requirements/upload",
            headers=auth_headers,
            files={"file": ("rollback.md", b"# rollback", "text/markdown")},
        )

    db_session.rollback()
    assert db_session.scalar(select(func.count(RequirementDocument.id))) == 0


def test_import_rolls_back_first_case_when_second_case_fails(
    db_session, monkeypatch
):
    doc = _add_document(db_session, ai_raw=_generated_payload())
    original_create = test_case_service.create_case
    calls = {"count": 0}

    def fail_second(db, data, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("second case failed")
        return original_create(db, data, **kwargs)

    monkeypatch.setattr(test_case_service, "create_case", fail_second)

    with pytest.raises(RuntimeError, match="second case failed"):
        requirement_service.import_cases(
            db_session,
            doc.id,
            [
                {"index": 0, "case_type": "manual", "title": "first"},
                {"index": 1, "case_type": "api", "title": "second"},
            ],
            project_id=1,
        )

    db_session.rollback()
    assert db_session.scalar(select(func.count(CaseModel.id))) == 0
    assert db_session.scalar(select(func.count(AuditLog.id))) == 0
    db_session.refresh(doc)
    assert doc.imported_count == 0
    assert doc.imported_func_indices == "[]"
    assert doc.imported_api_indices == "[]"


def test_import_edited_values_is_idempotent_and_tracks_cumulative_indices(
    client, auth_headers, db_session
):
    doc = _add_document(db_session, ai_raw=_generated_payload())
    body = {
        "indices": [0, 1],
        "edited_cases": [
            {
                "index": 0,
                "title": "edited case",
                "priority": "P0",
                "domain": "需求服务",
                "module": "导入",
                "preconditions": "edited precondition",
                "steps": "[{\"step\": 1, \"desc\": \"edited\"}]",
                "expected_result": "edited result",
            }
        ],
    }

    first = client.post(
        f"/api/v1/requirements/{doc.id}/import",
        headers=auth_headers,
        json=body,
    )
    assert first.status_code == 200
    assert first.json()["data"] == {"imported": 2, "skipped": 0, "total": 2, "plan_id": None, "plan_name": ""}

    second = client.post(
        f"/api/v1/requirements/{doc.id}/import",
        headers=auth_headers,
        json=body,
    )
    assert second.status_code == 200
    assert second.json()["data"] == {"imported": 0, "skipped": 2, "total": 2, "plan_id": None, "plan_name": ""}

    rows = list(
        db_session.scalars(
            select(CaseModel).order_by(CaseModel.source_case_index)
        )
    )
    assert len(rows) == 2
    assert rows[0].title == "edited case"
    assert rows[0].preconditions == "edited precondition"
    assert rows[0].expected_result == "edited result"
    db_session.refresh(doc)
    assert json.loads(doc.imported_func_indices) == [0]
    assert json.loads(doc.imported_api_indices) == [1]
    assert doc.imported_func_count == 1
    assert doc.imported_api_count == 1
    assert doc.imported_count == 2


def test_database_uniqueness_guards_concurrent_import_identity(
    db_session,
):
    doc = _add_document(db_session, ai_raw=_generated_payload())
    first = CaseModel(
        project_id=1,
        title="first importer",
        source="ai_generated",
        source_doc_id=doc.id,
        source_case_index=0,
    )
    db_session.add(first)
    db_session.commit()

    duplicate = CaseModel(
        project_id=1,
        title="concurrent importer",
        source="ai_generated",
        source_doc_id=doc.id,
        source_case_index=0,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    assert db_session.scalar(
        select(func.count(CaseModel.id)).where(
            CaseModel.project_id == 1,
            CaseModel.source_doc_id == doc.id,
            CaseModel.source_case_index == 0,
        )
    ) == 1


def test_import_and_review_edits_roll_back_when_audit_fails(
    client, auth_headers, db_session, monkeypatch,
):
    doc = _add_document(db_session, ai_raw=_generated_payload())

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(audit_service, "write_audit", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            f"/api/v1/requirements/{doc.id}/import",
            headers=auth_headers,
            json={
                "indices": [0],
                "edited_cases": [{"index": 0, "title": "must roll back"}],
            },
        )

    assert db_session.scalar(select(func.count(CaseModel.id))) == 0
    assert db_session.scalar(select(func.count(RequirementReview.id))) == 0
    db_session.refresh(doc)
    assert doc.imported_count == 0
    assert doc.imported_func_indices == "[]"


def test_review_queue_edit_approve_and_reject_persist(
    client, auth_headers, db_session
):
    doc = _add_document(db_session, ai_raw=_generated_payload())

    initial = client.get(
        f"/api/v1/requirements/{doc.id}/review-state", headers=auth_headers
    )
    assert initial.status_code == 200
    assert initial.json()["data"]["summary"] == {
        "total": 2,
        "approved": 0,
        "rejected": 0,
        "pending": 2,
    }

    edited = client.post(
        f"/api/v1/requirements/{doc.id}/review/0",
        headers=auth_headers,
        json={"action": "edit", "edited_data": {"title": "review-edited"}},
    )
    assert edited.status_code == 200

    approved = client.post(
        f"/api/v1/requirements/{doc.id}/review/0",
        headers=auth_headers,
        json={"action": "approve"},
    )
    assert approved.status_code == 200
    rejected = client.post(
        f"/api/v1/requirements/{doc.id}/review/1",
        headers=auth_headers,
        json={"action": "reject"},
    )
    assert rejected.status_code == 200

    db_session.expire_all()
    restored = client.get(
        f"/api/v1/requirements/{doc.id}/review-state", headers=auth_headers
    )
    data = restored.json()["data"]
    assert data["summary"] == {
        "total": 2,
        "approved": 1,
        "rejected": 1,
        "pending": 0,
    }
    assert data["functional_cases"][0]["edited_data"]["title"] == "review-edited"
    assert db_session.scalar(
        select(func.count(RequirementReview.id)).where(
            RequirementReview.requirement_id == doc.id
        )
    ) == 2


def test_delete_requirement_cleans_review_queue_and_commits_audit(
    client, auth_headers, db_session,
):
    doc = _add_document(db_session, ai_raw=_generated_payload())
    db_session.add(
        RequirementReview(
            requirement_id=doc.id,
            case_index=0,
            case_type="manual",
            status="approved",
        )
    )
    db_session.commit()
    doc_id = doc.id

    response = client.delete(
        f"/api/v1/requirements/{doc_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    db_session.rollback()
    assert db_session.get(RequirementDocument, doc_id) is None
    assert db_session.scalar(
        select(func.count(RequirementReview.id)).where(
            RequirementReview.requirement_id == doc_id
        )
    ) == 0
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "requirement:delete"
        )
    ) == 1


def test_review_queue_rejects_foreign_document_and_unknown_index(
    client, auth_headers, db_session
):
    foreign = _add_document(db_session, project_id=2, ai_raw=_generated_payload())

    foreign_response = client.get(
        f"/api/v1/requirements/{foreign.id}/review-state", headers=auth_headers
    )
    assert foreign_response.status_code == 404
    assert "original case" not in foreign_response.text

    own = _add_document(db_session, ai_raw=_generated_payload())
    missing_index = client.post(
        f"/api/v1/requirements/{own.id}/review/99",
        headers=auth_headers,
        json={"action": "approve"},
    )
    assert missing_index.status_code == 404


def test_confirm_extraction_preserves_original_assessment_and_metadata(
    client, auth_headers, db_session
):
    extraction = {
        "modules": [{"id": "old", "name": "old", "function_points": []}],
        "overall_assessment": "keep this assessment",
        "extraction_summary": "keep summary",
        "changelog": {"versions": [{"version": "1.0"}]},
    }
    doc = _add_document(db_session, extraction_raw=extraction)

    response = client.post(
        f"/api/v1/requirements/{doc.id}/extraction/confirm",
        headers=auth_headers,
        json={
            "action": "confirm",
            "modules": [{"id": "new", "name": "edited", "function_points": []}],
            "rejected_modules": [],
            "rejected_notes": "",
        },
    )
    assert response.status_code == 200

    db_session.refresh(doc)
    saved = json.loads(doc.extraction_raw)
    assert saved["overall_assessment"] == "keep this assessment"
    assert saved["extraction_summary"] == "keep summary"
    assert saved["changelog"] == extraction["changelog"]
    assert saved["modules"][0]["name"] == "edited"


def test_reject_extraction_persists_reset_state_and_audit_after_refresh(
    client, auth_headers, db_session
):
    doc = _add_document(
        db_session,
        extraction_raw={
            "modules": [{"id": "old", "name": "old", "function_points": []}],
            "overall_assessment": "keep assessment for the next review",
        },
    )

    rejected = client.post(
        f"/api/v1/requirements/{doc.id}/extraction/confirm",
        headers=auth_headers,
        json={
            "action": "reject",
            "rejected_modules": ["old"],
            "rejected_notes": "拆分粒度不正确",
        },
    )

    assert rejected.status_code == 200
    assert rejected.json()["data"]["extraction_status"] == "not_started"

    db_session.expire_all()
    restored = client.get(
        f"/api/v1/requirements/{doc.id}/extraction",
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["extraction_status"] == "not_started"
    assert (
        restored.json()["data"]["overall_assessment"]
        == "keep assessment for the next review"
    )

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "requirement:extract:confirm",
            AuditLog.target == f"doc#{doc.id}",
        )
    )
    assert audit is not None
    assert "拒绝功能拆分" in audit.detail
    assert "拆分粒度不正确" in audit.detail


def test_inherited_aliases_serialize_with_public_wire_names():
    fp = FunctionPointSchema(
        title="unchanged feature",
        _inherited=True,
        _from_version="1.0",
    )
    case = AIGeneratedCase(
        title="inherited case",
        _inherited=True,
        _from_version="1.0",
    )

    assert fp.model_dump(by_alias=True)["_inherited"] is True
    assert fp.model_dump(by_alias=True)["_from_version"] == "1.0"
    assert case.model_dump(by_alias=True)["_inherited"] is True
    assert case.model_dump(by_alias=True)["_from_version"] == "1.0"


def test_inherited_function_point_markers_survive_database_reload(
    client, auth_headers, db_session
):
    doc = _add_document(
        db_session,
        extraction_raw={
            "modules": [
                {
                    "id": "module-1",
                    "name": "unchanged module",
                    "function_points": [
                        {
                            "id": "fp-1",
                            "title": "unchanged feature",
                            "_inherited": True,
                            "_from_version": "1.0",
                        }
                    ],
                }
            ],
            "overall_assessment": "confirmed",
        },
    )

    db_session.expire_all()
    response = client.get(
        f"/api/v1/requirements/{doc.id}/extraction",
        headers=auth_headers,
    )

    assert response.status_code == 200
    function_point = response.json()["data"]["modules"][0]["function_points"][0]
    assert function_point["_inherited"] is True
    assert function_point["_from_version"] == "1.0"


def test_generate_persists_inherited_cases_before_cases_get_and_import(
    client, auth_headers, db_session, monkeypatch
):
    parent = _add_document(
        db_session,
        title="parent",
        ai_raw={
            "functional_cases": [
                {
                    "title": "unchanged feature happy path",
                    "priority": "P0",
                    "steps": [],
                    "expected_result": "parent result",
                }
            ],
            "api_cases": [],
        },
    )
    parent.version = "1.0"
    child = _add_document(
        db_session,
        title="child",
        extraction_raw={
            "modules": [
                {
                    "id": "inherited",
                    "name": "inherited",
                    "function_points": [
                        {
                            "id": "fp-1",
                            "title": "unchanged feature",
                            "name": "unchanged feature",
                            "_inherited": True,
                            "_from_version": "1.0",
                        }
                    ],
                }
            ],
            "overall_assessment": "confirmed",
        },
    )
    child.version = "2.0"
    child.parent_id = parent.id
    db_session.commit()

    async def fake_generate(**_kwargs):
        return {
            "functional_cases": [],
            "api_cases": [],
            "requirement_analysis": {
                "extracted_requirements": [],
                "overall_assessment": "",
            },
        }

    from app.services import ai_service

    monkeypatch.setattr(ai_service, "generate_test_cases", fake_generate)

    response = client.post(
        f"/api/v1/requirements/{child.id}/generate",
        headers=auth_headers,
        json={"use_extraction": True},
    )
    assert response.status_code == 200
    generated = response.json()["data"]["functional_cases"]
    assert len(generated) == 1
    assert generated[0]["_inherited"] is True
    assert generated[0]["_from_version"] == "1.0"

    restored = client.get(
        f"/api/v1/requirements/{child.id}/cases", headers=auth_headers
    )
    assert len(restored.json()["data"]["functional_cases"]) == 1
    assert "unchanged feature" in restored.json()["data"]["functional_cases"][0]["title"]

    imported = client.post(
        f"/api/v1/requirements/{child.id}/import",
        headers=auth_headers,
        json={"indices": [0]},
    )
    assert imported.status_code == 200
    assert imported.json()["data"] == {"imported": 1, "skipped": 0, "total": 1, "plan_id": None, "plan_name": ""}

    db_session.expire_all()
    imported_case = db_session.scalar(
        select(CaseModel).where(
            CaseModel.project_id == 1,
            CaseModel.source_doc_id == child.id,
            CaseModel.source_case_index == 0,
        )
    )
    assert imported_case is not None
    assert imported_case.title.startswith("[沿用自1.0]")
    assert "unchanged feature" in imported_case.title

    repeated = client.post(
        f"/api/v1/requirements/{child.id}/import",
        headers=auth_headers,
        json={"indices": [0]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["data"] == {"imported": 0, "skipped": 1, "total": 1, "plan_id": None, "plan_name": ""}


def test_match_api_requires_ownership_and_confirmed_selection_survives_refresh(
    client, auth_headers, db_session
):
    foreign = _add_document(db_session, project_id=2, title="foreign match")
    denied = client.post(
        f"/api/v1/requirements/{foreign.id}/match-api",
        headers=auth_headers,
        json={"integration_reqs": [], "service_id": None},
    )
    assert denied.status_code == 404
    assert "foreign match" not in denied.text

    own = _add_document(db_session, title="own match")
    service = ApiService(project_id=1, name="users", display_name="Users")
    db_session.add(service)
    db_session.flush()
    endpoint = ApiEndpoint(
        project_id=1,
        service_id=service.id,
        method="GET",
        path="/users",
        summary="获取用户列表",
    )
    db_session.add(endpoint)
    db_session.commit()

    matched = client.post(
        f"/api/v1/requirements/{own.id}/match-api",
        headers=auth_headers,
        json={
            "integration_reqs": [
                {"id": "REQ-1", "title": "获取用户列表", "description": "查询 users"}
            ],
            "service_id": service.id,
        },
    )
    assert matched.status_code == 200
    assert len(matched.json()["data"]) == 1
    db_session.refresh(own)
    assert own.linked_swagger_id is None

    confirmed = client.post(
        f"/api/v1/requirements/{own.id}/match-api/confirm",
        headers=auth_headers,
        json={"service_id": service.id, "endpoint_ids": [endpoint.id]},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["data"] == {
        "service_id": service.id,
        "endpoint_ids": [endpoint.id],
    }

    db_session.expire_all()
    restored = client.get(
        f"/api/v1/requirements/{own.id}/match-api/selection",
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["data"] == {
        "service_id": service.id,
        "endpoint_ids": [endpoint.id],
    }
    own = db_session.get(RequirementDocument, own.id)
    assert own.linked_swagger_id == service.id
    assert json.loads(own.linked_api_endpoint_ids) == [endpoint.id]


def test_requirement_coverage_rejects_foreign_document(
    client, auth_headers, db_session
):
    foreign = _add_document(db_session, project_id=2, title="foreign coverage")

    response = client.get(
        f"/api/v1/requirements/{foreign.id}/coverage", headers=auth_headers
    )
    assert response.status_code == 404
    assert "foreign coverage" not in response.text


def test_requirement_coverage_uses_real_case_plan_execution_and_defect_links(
    client, auth_headers, db_session
):
    doc = _add_document(db_session, title="coverage source")
    doc.imported_count = 2
    first_case = CaseModel(
        project_id=1,
        case_id="B48-COV-001",
        title="planned and passed",
        source="ai_generated",
        source_doc_id=doc.id,
        source_case_index=0,
    )
    second_case = CaseModel(
        project_id=1,
        case_id="B48-COV-002",
        title="unplanned with defect",
        source="ai_generated",
        source_doc_id=doc.id,
        source_case_index=1,
    )
    db_session.add_all([first_case, second_case])
    db_session.flush()

    plan = PlanModel(
        project_id=1,
        plan_id="B48-COV-PLAN",
        name="Batch 48 coverage plan",
        creator_id=1,
    )
    db_session.add(plan)
    db_session.flush()
    plan_case = PlanCaseModel(plan_id=plan.id, case_id=first_case.id)
    db_session.add(plan_case)
    db_session.flush()
    db_session.add(
        ExecutionModel(
            plan_case_id=plan_case.id,
            executor_id=1,
            status="passed",
            actual_result="passed",
        )
    )
    db_session.add(
        Defect(
            project_id=1,
            defect_id="B48-COV-DEFECT",
            title="coverage-linked defect",
            case_id=second_case.id,
            creator_id=1,
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/requirements/{doc.id}/coverage",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["document_id"] == doc.id
    assert data["total_cases"] == 2
    assert data["imported_count"] == 2
    assert data["cases_in_plans"] == 1
    assert data["cases_executed"] == 1
    assert data["cases_passed"] == 1
    assert data["cases_with_defects"] == 1
    assert data["coverage_rate"] == 50.0
    assert data["execution_rate"] == 50.0
    assert data["pass_rate"] == 100.0
    cases = {item["case_id"]: item for item in data["cases"]}
    assert cases["B48-COV-001"]["in_plan"] is True
    assert cases["B48-COV-001"]["passed"] is True
    assert cases["B48-COV-002"]["defect_count"] == 1
