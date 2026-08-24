"""Batch 48 production acceptance coverage for requirement module APIs."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.api_asset import ApiEndpoint, ApiService
from app.models.audit import AuditLog
from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage
from app.models.requirement import RequirementDocument
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.release_bundle import ReleaseBundle


def _bundle(db_session, *, project_id: int, name: str) -> ReleaseBundle:
    bundle = ReleaseBundle(
        project_id=project_id,
        name=name,
        client_version="1.0.0",
        admin_version="1.0.0",
    )
    db_session.add(bundle)
    db_session.flush()
    return bundle


def _module(
    db_session,
    *,
    project_id: int,
    bundle_id: int,
    name: str,
    platform: str,
    node_type: str = "module",
    parent_module_id: int | None = None,
    change_type: str = "new",
) -> RequirementModule:
    module = RequirementModule(
        project_id=project_id,
        release_bundle_id=bundle_id,
        name=name,
        platform=platform,
        node_type=node_type,
        parent_module_id=parent_module_id,
        change_type=change_type,
    )
    db_session.add(module)
    db_session.flush()
    return module


def _document(
    db_session,
    *,
    project_id: int = 1,
    title: str = "Batch48 API mapping",
) -> RequirementDocument:
    document = RequirementDocument(
        project_id=project_id,
        creator_id=1,
        title=title,
        file_type="md",
        source_ref=f"{title}.md",
        content="# API requirement",
        status="parsed",
    )
    db_session.add(document)
    db_session.flush()
    return document


def test_lazy_children_returns_grandchildren(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    parent = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="parent",
        platform="APP",
    )
    child = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="child",
        platform="APP",
        node_type="page",
        parent_module_id=parent.id,
    )
    grandchild = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="grandchild",
        platform="APP",
        node_type="function_point",
        parent_module_id=child.id,
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/requirement-modules/bundle/{bundle.id}/children/{parent.id}",
        headers=auth_headers,
    )
    full_tree = client.get(
        f"/api/v1/requirement-modules/bundle/{bundle.id}/tree",
        headers=auth_headers,
    )

    assert response.status_code == full_tree.status_code == 200
    nodes = response.json()["data"]
    assert [node["id"] for node in nodes] == [child.id]
    assert [node["id"] for node in nodes[0]["children"]] == [grandchild.id]
    assert nodes[0]["child_count"] == 1
    full_root = full_tree.json()["data"]["roots"][0]
    full_child = full_root["children"][0]
    assert full_root["id"] == parent.id
    assert full_root["child_count"] == 1
    assert full_child["id"] == nodes[0]["id"] == child.id
    assert full_child["child_count"] == nodes[0]["child_count"] == 1
    assert [item["id"] for item in full_child["children"]] == [
        item["id"] for item in nodes[0]["children"]
    ] == [grandchild.id]


@pytest.mark.parametrize("foreign_target", ["bundle", "parent"])
def test_lazy_children_rejects_foreign_project_resources(
    foreign_target, client, auth_headers, db_session,
):
    own_bundle = _bundle(db_session, project_id=1, name="own")
    foreign_bundle = _bundle(db_session, project_id=2, name="foreign")
    foreign_parent = _module(
        db_session,
        project_id=2,
        bundle_id=foreign_bundle.id,
        name="secret parent",
        platform="APP",
    )
    db_session.commit()

    bundle_id = foreign_bundle.id if foreign_target == "bundle" else own_bundle.id
    response = client.get(
        f"/api/v1/requirement-modules/bundle/{bundle_id}/children/{foreign_parent.id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "secret parent" not in response.text


def test_module_tree_ignores_cross_project_rows_in_same_bundle(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    own = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="own",
        platform="APP",
    )
    _module(
        db_session,
        project_id=2,
        bundle_id=bundle.id,
        name="corrupt foreign",
        platform="APP",
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/requirement-modules/bundle/{bundle.id}/tree",
        headers=auth_headers,
    )

    assert response.status_code == 200
    roots = response.json()["data"]["roots"]
    assert [node["id"] for node in roots] == [own.id]


def test_module_list_filters_and_count_use_identical_conditions(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    parent = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="订单中心",
        platform="APP",
    )
    first = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="订单查询",
        platform="APP",
        node_type="page",
        parent_module_id=parent.id,
        change_type="modified",
    )
    second = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="订单详情",
        platform="APP",
        node_type="page",
        parent_module_id=parent.id,
        change_type="modified",
    )
    _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="订单新建",
        platform="APP",
        node_type="page",
        parent_module_id=parent.id,
        change_type="new",
    )
    _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="订单详情字段",
        platform="APP",
        node_type="function_point",
        parent_module_id=first.id,
        change_type="modified",
    )
    _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="运营订单",
        platform="ADMIN",
        node_type="page",
        parent_module_id=parent.id,
        change_type="modified",
    )
    _module(
        db_session,
        project_id=2,
        bundle_id=bundle.id,
        name="订单 secret",
        platform="APP",
        node_type="page",
        parent_module_id=parent.id,
        change_type="modified",
    )
    db_session.commit()

    filters = {
        "release_bundle_id": bundle.id,
        "node_type": "page",
        "platform": "APP",
        "change_type": "modified",
        "parent_module_id": parent.id,
        "keyword": "订单",
        "page": 1,
        "page_size": 1,
    }
    page_one = client.get(
        "/api/v1/requirement-modules", headers=auth_headers, params=filters,
    )
    repeated_page_one = client.get(
        "/api/v1/requirement-modules", headers=auth_headers, params=filters,
    )
    page_two = client.get(
        "/api/v1/requirement-modules",
        headers=auth_headers,
        params={**filters, "page": 2},
    )
    roots_only = client.get(
        "/api/v1/requirement-modules",
        headers=auth_headers,
        params={
            "release_bundle_id": bundle.id,
            "node_type": "module",
            "platform": "APP",
            "change_type": "new",
            "parent_module_id": 0,
        },
    )

    assert (
        page_one.status_code
        == repeated_page_one.status_code
        == page_two.status_code
        == roots_only.status_code
        == 200
    )
    first_page = page_one.json()["data"]
    repeated_first_page = repeated_page_one.json()["data"]
    second_page = page_two.json()["data"]
    assert first_page["total"] == second_page["total"] == 2
    assert [item["id"] for item in first_page["items"]] == [first.id]
    assert [item["id"] for item in second_page["items"]] == [second.id]
    assert repeated_first_page == first_page
    assert roots_only.json()["data"]["total"] == 1
    assert [item["id"] for item in roots_only.json()["data"]["items"]] == [parent.id]


def test_repeated_module_extraction_reuses_natural_identity_and_keeps_manual_data(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="Batch48 extraction")
    evidence_job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/redacted",
        status="success",
    )
    db_session.add(evidence_job)
    db_session.flush()
    db_session.add(
        LanhuEvidencePage(
            job_id=evidence_job.id,
            project_id=1,
            page_id="page-match-list",
            page_name="比赛列表",
            page_path="APP端/赛事/比赛列表",
            folder="APP端/赛事",
            order_index=0,
            merged_text="比赛列表正文",
            local_url="file:///redacted/match-list.html",
        )
    )
    manual = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="人工补充模块",
        platform="APP",
    )
    manual.description = "不得由自动提取删除"
    manual.source_version = "manual"
    db_session.commit()

    payload = {
        "evidence_job_id": evidence_job.id,
        "source_version": "14.1.0",
    }
    first = client.post(
        f"/api/v1/requirement-modules/bundle/{bundle.id}/extract",
        headers=auth_headers,
        json=payload,
    )
    assert first.status_code == 200
    first_ids = first.json()["data"]["module_ids"]
    first_count = db_session.scalar(
        select(func.count(RequirementModule.id)).where(
            RequirementModule.project_id == 1,
            RequirementModule.release_bundle_id == bundle.id,
        )
    )
    extracted_root = db_session.get(RequirementModule, first_ids[0])
    extracted_root.description = "人工审核后的说明"
    db_session.commit()

    second = client.post(
        f"/api/v1/requirement-modules/bundle/{bundle.id}/extract",
        headers=auth_headers,
        json=payload,
    )

    assert second.status_code == 200
    assert second.json()["data"]["module_ids"] == first_ids
    assert db_session.scalar(
        select(func.count(RequirementModule.id)).where(
            RequirementModule.project_id == 1,
            RequirementModule.release_bundle_id == bundle.id,
        )
    ) == first_count
    db_session.expire_all()
    assert db_session.get(RequirementModule, extracted_root.id).description == "人工审核后的说明"
    assert db_session.get(RequirementModule, manual.id).description == "不得由自动提取删除"


def test_interactions_reject_non_page_module_and_invalid_merge_state(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="not a page",
        platform="APP",
    )
    page = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="page",
        platform="APP",
        node_type="page",
    )
    db_session.commit()

    wrong_node = client.put(
        f"/api/v1/requirement-modules/{module.id}/interactions",
        headers=auth_headers,
        json={"merge": True, "interactions": [{"trigger": "should not persist"}]},
    )
    invalid_state = client.put(
        f"/api/v1/requirement-modules/{page.id}/interactions",
        headers=auth_headers,
        json={"merge": "append", "interactions": []},
    )

    assert wrong_node.status_code == 200
    assert wrong_node.json()["code"] == 400
    assert invalid_state.status_code == 422
    db_session.expire_all()
    assert db_session.get(RequirementModule, module.id).page_interactions == "[]"
    assert db_session.get(RequirementModule, page.id).page_interactions == "[]"
    assert db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "module:save_interactions"
        )
    ) == 0


def test_page_interactions_merge_replace_and_audit_persist(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    page = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="home",
        platform="APP",
        node_type="page",
    )
    db_session.commit()

    first = client.put(
        f"/api/v1/requirement-modules/{page.id}/interactions",
        headers=auth_headers,
        json={
            "merge": True,
            "interactions": [
                {
                    "trigger": "点击详情",
                    "target_page": "详情页",
                    "interaction_type": "navigation",
                }
            ],
        },
    )
    duplicate_merge = client.put(
        f"/api/v1/requirement-modules/{page.id}/interactions",
        headers=auth_headers,
        json={
            "merge": True,
            "interactions": [
                {
                    "trigger": "点击详情",
                    "target_page": "详情页",
                    "interaction_type": "navigation",
                }
            ],
        },
    )
    replace = client.put(
        f"/api/v1/requirement-modules/{page.id}/interactions",
        headers=auth_headers,
        json={
            "merge": False,
            "interactions": [
                {
                    "id": "saved-region-61",
                    "trigger": "打开筛选",
                    "target_page": "",
                    "interaction_type": "dynamic_filter",
                    "admin_config_source": "筛选配置",
                    "x": 12,
                    "y": 18,
                    "width": 220,
                    "height": 64,
                }
            ],
        },
    )

    assert first.status_code == duplicate_merge.status_code == replace.status_code == 200
    assert first.json()["data"]["interaction_count"] == 1
    assert duplicate_merge.json()["data"]["interaction_count"] == 1
    assert replace.json()["data"]["interaction_count"] == 1
    db_session.rollback()
    db_session.refresh(page)
    assert "打开筛选" in page.page_interactions
    assert "点击详情" not in page.page_interactions
    saved = json.loads(page.page_interactions)
    assert saved[0]["id"] == "saved-region-61"
    assert {key: saved[0][key] for key in ("x", "y", "width", "height")} == {
        "x": 12.0,
        "y": 18.0,
        "width": 220.0,
        "height": 64.0,
    }
    assert db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "module:save_interactions"
        )
    ) == 3


def test_admin_link_requires_valid_direction_and_same_bundle(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    other_bundle = _bundle(db_session, project_id=1, name="other")
    client_module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="client",
        platform="APP",
    )
    admin_module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="admin",
        platform="ADMIN",
    )
    other_admin = _module(
        db_session,
        project_id=1,
        bundle_id=other_bundle.id,
        name="other admin",
        platform="ADMIN",
    )
    db_session.commit()

    valid = client.post(
        "/api/v1/requirement-modules/admin-links",
        headers=auth_headers,
        json={
            "client_module_id": client_module.id,
            "admin_module_id": admin_module.id,
            "relation_type": "configures",
        },
    )
    assert valid.status_code == 200

    reversed_direction = client.post(
        "/api/v1/requirement-modules/admin-links",
        headers=auth_headers,
        json={
            "client_module_id": admin_module.id,
            "admin_module_id": client_module.id,
            "relation_type": "configures",
        },
    )
    assert reversed_direction.status_code == 400

    cross_bundle = client.post(
        "/api/v1/requirement-modules/admin-links",
        headers=auth_headers,
        json={
            "client_module_id": client_module.id,
            "admin_module_id": other_admin.id,
            "relation_type": "links_to_admin",
        },
    )
    assert cross_bundle.status_code == 400

    invalid_relation = client.post(
        "/api/v1/requirement-modules/admin-links",
        headers=auth_headers,
        json={
            "client_module_id": client_module.id,
            "admin_module_id": admin_module.id,
            "relation_type": "contains",
        },
    )
    assert invalid_relation.status_code == 422


def test_admin_link_duplicate_returns_conflict(
    client, auth_headers, db_session,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    client_module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="client",
        platform="WEB",
    )
    admin_module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="admin",
        platform="ADMIN",
    )
    db_session.commit()
    payload = {
        "client_module_id": client_module.id,
        "admin_module_id": admin_module.id,
        "relation_type": "links_to_admin",
    }

    assert client.post(
        "/api/v1/requirement-modules/admin-links",
        headers=auth_headers,
        json=payload,
    ).status_code == 200
    duplicate = client.post(
        "/api/v1/requirement-modules/admin-links",
        headers=auth_headers,
        json=payload,
    )

    assert duplicate.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(ModuleAdminLink)) == 1

    db_session.add(ModuleAdminLink(
        project_id=1,
        client_module_id=client_module.id,
        admin_module_id=admin_module.id,
        relation_type="links_to_admin",
        confidence=0.5,
        evidence="simulated concurrent loser",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(ModuleAdminLink)) == 1


def test_admin_link_and_audit_are_atomic(
    client, auth_headers, db_session, monkeypatch,
):
    bundle = _bundle(db_session, project_id=1, name="current")
    client_module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="client",
        platform="PC",
    )
    admin_module = _module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="admin",
        platform="ADMIN",
    )
    db_session.commit()

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(
        "app.api.v1.requirement_modules_links.audit_service.write_audit",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit storage unavailable"):
        client.post(
            "/api/v1/requirement-modules/admin-links",
            headers=auth_headers,
            json={
                "client_module_id": client_module.id,
                "admin_module_id": admin_module.id,
                "relation_type": "configures",
            },
        )

    assert db_session.scalar(select(func.count()).select_from(ModuleAdminLink)) == 0
    # auth.* 审计（认证事件，B12 起记录）不属于本链路副作用
    assert db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.action.not_like("auth.%"))
    ) == 0


def test_api_match_rejects_missing_document_foreign_service_and_endpoint(
    client, auth_headers, db_session,
):
    own_document = _document(db_session)
    own_service = ApiService(project_id=1, name="own", display_name="Own")
    foreign_service = ApiService(
        project_id=2, name="foreign", display_name="Foreign secret"
    )
    db_session.add_all([own_service, foreign_service])
    db_session.flush()
    foreign_endpoint = ApiEndpoint(
        project_id=2,
        service_id=foreign_service.id,
        method="GET",
        path="/foreign-secret",
        summary="Foreign endpoint secret",
    )
    db_session.add(foreign_endpoint)
    db_session.commit()

    missing_document = client.post(
        "/api/v1/requirements/999999/match-api",
        headers=auth_headers,
        json={"integration_reqs": [], "service_id": None},
    )
    foreign_service_response = client.post(
        f"/api/v1/requirements/{own_document.id}/match-api",
        headers=auth_headers,
        json={"integration_reqs": [], "service_id": foreign_service.id},
    )
    foreign_endpoint_response = client.post(
        f"/api/v1/requirements/{own_document.id}/match-api/confirm",
        headers=auth_headers,
        json={
            "service_id": own_service.id,
            "endpoint_ids": [foreign_endpoint.id],
        },
    )

    assert missing_document.status_code == 404
    assert foreign_service_response.status_code == 404
    assert "Foreign secret" not in foreign_service_response.text
    assert foreign_endpoint_response.status_code == 400
    assert "Foreign endpoint secret" not in foreign_endpoint_response.text
    db_session.refresh(own_document)
    assert own_document.linked_swagger_id is None
    assert own_document.linked_api_endpoint_ids == "[]"
    assert db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "requirement:match-api:confirm"
        )
    ) == 0


def test_api_match_confirmation_persists_audit_and_coverage_trace(
    client, auth_headers, db_session,
):
    document = _document(db_session, title="Traceable requirement")
    service = ApiService(project_id=1, name="trace", display_name="Trace")
    db_session.add(service)
    db_session.flush()
    endpoint = ApiEndpoint(
        project_id=1,
        service_id=service.id,
        method="GET",
        path="/trace",
        summary="Trace endpoint",
    )
    db_session.add(endpoint)
    db_session.commit()

    confirmed = client.post(
        f"/api/v1/requirements/{document.id}/match-api/confirm",
        headers=auth_headers,
        json={
            "service_id": service.id,
            "endpoint_ids": [endpoint.id, endpoint.id],
        },
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["data"] == {
        "service_id": service.id,
        "endpoint_ids": [endpoint.id],
    }
    db_session.expire_all()
    persisted = db_session.get(RequirementDocument, document.id)
    assert persisted.linked_swagger_id == service.id
    assert json.loads(persisted.linked_api_endpoint_ids) == [endpoint.id]

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "requirement:match-api:confirm",
            AuditLog.target == f"doc#{document.id}",
        )
    )
    assert audit is not None
    assert audit.project_id == 1
    assert str(service.id) in audit.detail
    assert "接口 1 个" in audit.detail

    restored = client.get(
        f"/api/v1/requirements/{document.id}/match-api/selection",
        headers=auth_headers,
    )
    coverage = client.get(
        f"/api/v1/requirements/{document.id}/coverage",
        headers=auth_headers,
    )
    assert restored.status_code == coverage.status_code == 200
    assert restored.json()["data"] == confirmed.json()["data"]
    coverage_data = coverage.json()["data"]
    assert coverage_data["document_id"] == document.id
    assert coverage_data["document_title"] == "Traceable requirement"
    assert coverage_data["document_status"] == "parsed"
    assert coverage_data["total_cases"] == 0
