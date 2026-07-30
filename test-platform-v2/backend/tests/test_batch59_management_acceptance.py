"""Batch 59 management-domain acceptance evidence for J02/J04/J19."""
from __future__ import annotations

from app.models.dataset import Dataset
from app.models.integration import IntegrationConfig
import pytest

from app.models.test_case import TestCase as CaseModel
from app.models.test_plan import TestPlan as PlanModel
from app.services.dataset_service import get_dataset_rows
from tests.batch59_factories import seed_case_plan_execution, seed_projects


def _headers_for_project(auth_headers: dict, project_id: int) -> dict:
    return {**auth_headers, "X-Project-Id": str(project_id)}


def test_j02_dashboard_counts_are_project_scoped_and_empty_project_is_zero(
    client,
    auth_headers,
    db_session,
) -> None:
    """P0 positive + negative: counts use the selected project and never leak names."""
    seed_projects(db_session)
    seed_case_plan_execution(db_session, project_id=1, suffix="OWN")
    seed_case_plan_execution(db_session, project_id=2, suffix="FOREIGN")

    own = client.get("/api/v1/dashboard/stats", headers=auth_headers)
    empty = client.get(
        "/api/v1/dashboard/stats",
        headers=_headers_for_project(auth_headers, 3),
    )

    assert own.status_code == 200
    assert empty.status_code == 200
    assert own.json()["data"]["total_cases"] == 1
    assert own.json()["data"]["total_plans"] == 1
    assert empty.json()["data"]["total_cases"] == 0
    assert empty.json()["data"]["total_plans"] == 0
    assert "FOREIGN" not in own.text

    assert db_session.query(CaseModel).filter_by(project_id=1).count() == 1
    assert db_session.query(PlanModel).filter_by(project_id=1).count() == 1


def test_j02_cross_project_dashboard_is_consistent_for_super_admin(
    client,
    auth_headers,
    db_session,
) -> None:
    """P0 return-value check: the global card totals match the persisted graph."""
    seed_projects(db_session)
    seed_case_plan_execution(db_session, project_id=1, suffix="OWN")
    seed_case_plan_execution(db_session, project_id=2, suffix="FOREIGN")

    response = client.get("/api/v1/dashboard/cross-project", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["aggregate"]["total_projects"] == 3
    assert data["aggregate"]["total_cases"] == 2
    assert data["aggregate"]["total_plans"] == 2
    assert {item["project_id"] for item in data["per_project"]} == {1, 2, 3}


def test_j04_dataset_pagination_and_cross_project_mutations_are_isolated(
    client,
    auth_headers,
    db_session,
) -> None:
    """P0/P1: page totals are stable and foreign detail/update/delete have no effect."""
    own_payloads = [
        {
            "name": f"Batch 59 dataset {index}",
            "source_type": "csv",
            "raw_content": f"id,name\n{index},row-{index}\n",
        }
        for index in range(3)
    ]
    own_ids = []
    for payload in own_payloads:
        created = client.post("/api/v1/datasets", json=payload, headers=auth_headers)
        assert created.status_code == 200
        assert created.json()["code"] == 0
        own_ids.append(created.json()["data"]["dataset"]["id"])

    foreign = Dataset(
        project_id=2,
        name="foreign-dataset",
        source_type="csv",
        raw_content="id\n99\n",
        row_count=1,
        columns_meta='["id"]',
    )
    db_session.add(foreign)
    db_session.commit()

    first = client.get("/api/v1/datasets?page=1&page_size=2", headers=auth_headers)
    repeated = client.get("/api/v1/datasets?page=1&page_size=2", headers=auth_headers)
    second = client.get("/api/v1/datasets?page=2&page_size=2", headers=auth_headers)

    assert first.status_code == repeated.status_code == second.status_code == 200
    assert first.json()["data"]["total"] == 3
    assert [item["id"] for item in first.json()["data"]["items"]] == [
        item["id"] for item in repeated.json()["data"]["items"]
    ]
    assert len(first.json()["data"]["items"]) == 2
    assert len(second.json()["data"]["items"]) == 1
    assert set(own_ids) == {
        item["id"]
        for page in (first, second)
        for item in page.json()["data"]["items"]
    }

    detail = client.get(f"/api/v1/datasets/{foreign.id}", headers=auth_headers)
    updated = client.put(
        f"/api/v1/datasets/{foreign.id}",
        json={"name": "stolen"},
        headers=auth_headers,
    )
    deleted = client.delete(f"/api/v1/datasets/{foreign.id}", headers=auth_headers)

    assert detail.status_code == updated.status_code == deleted.status_code == 200
    assert detail.json()["code"] == 404
    assert updated.json()["code"] == 404
    assert deleted.json()["code"] == 404
    db_session.expire_all()
    assert db_session.get(Dataset, foreign.id).name == "foreign-dataset"
    with pytest.raises(ValueError, match="not found"):
        get_dataset_rows(db_session, foreign.id, project_id=1)


def test_j04_dataset_rejects_invalid_content_without_side_effect(
    client,
    auth_headers,
    db_session,
) -> None:
    """P1 input/business check: malformed JSON does not persist a dataset."""
    response = client.post(
        "/api/v1/datasets",
        json={
            "name": "invalid-json",
            "source_type": "json",
            "raw_content": "{not-json}",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["code"] == 1
    assert db_session.query(Dataset).count() == 0


def test_j04_integration_crud_masks_secret_and_is_project_scoped(
    client,
    auth_headers,
    db_session,
) -> None:
    """P0 security: plaintext credentials never return and foreign IDs stay hidden."""
    secret = '{"token":"batch59-secret-value"}'
    created = client.post(
        "/api/v1/integrations",
        json={
            "name": "Batch 59 Jira",
            "provider_type": "jira",
            "base_url": "https://jira.example.test",
            "auth_json": secret,
            "enabled": False,
        },
        headers=auth_headers,
    )

    assert created.status_code == 200
    assert created.json()["data"]["auth_json"] == "********"
    assert secret not in created.text
    integration_id = created.json()["data"]["id"]

    detail = client.get(f"/api/v1/integrations/{integration_id}", headers=auth_headers)
    listed = client.get("/api/v1/integrations", headers=auth_headers)
    assert detail.status_code == listed.status_code == 200
    assert detail.json()["data"]["auth_json"] == "********"
    assert secret not in detail.text
    assert secret not in listed.text

    db_session.add(
        IntegrationConfig(
            project_id=2,
            name="foreign-integration",
            auth_json="foreign-encrypted-value",
        )
    )
    db_session.commit()
    foreign = db_session.query(IntegrationConfig).filter_by(project_id=2).one()

    foreign_detail = client.get(
        f"/api/v1/integrations/{foreign.id}",
        headers=auth_headers,
    )
    foreign_update = client.put(
        f"/api/v1/integrations/{foreign.id}",
        json={"name": "stolen"},
        headers=auth_headers,
    )
    foreign_delete = client.delete(
        f"/api/v1/integrations/{foreign.id}",
        headers=auth_headers,
    )

    assert foreign_detail.status_code == 404
    assert foreign_update.status_code == 404
    assert foreign_delete.status_code == 404
    db_session.expire_all()
    assert db_session.get(IntegrationConfig, foreign.id).name == "foreign-integration"
