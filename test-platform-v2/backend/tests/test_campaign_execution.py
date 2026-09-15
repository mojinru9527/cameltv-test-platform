from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.modules.campaign_execution.service as campaign_service
from app.core.exceptions import APIException
from app.modules.campaign_execution.models import CampaignItem, TestCampaign as CampaignRow
from app.modules.campaign_execution.service import start_campaign


def _campaign(db, *, project_id: int = 1) -> CampaignRow:
    row = CampaignRow(
        project_id=project_id,
        name=f"campaign-{project_id}",
        type="adhoc",
        environment_id=7,
        created_by=1,
    )
    db.add(row)
    db.flush()
    return row


def _item(db, campaign_id: int, sequence: int, *, enabled: bool = True) -> CampaignItem:
    row = CampaignItem(
        campaign_id=campaign_id,
        asset_type="api",
        asset_id=100 + sequence,
        sequence=sequence,
        enabled=enabled,
        config_json=(
            '{"scenario_id":10,"scenario_version_id":20,'
            '"contract_version_id":30,"environment_snapshot_id":40}'
        ),
    )
    db.add(row)
    return row


def test_start_campaign_materializes_enabled_items_in_sequence(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _campaign(db_session)
    _item(db_session, campaign.id, 2)
    _item(db_session, campaign.id, 1)
    _item(db_session, campaign.id, 3, enabled=False)
    db_session.commit()

    calls: list[dict] = []

    def fake_create_run(db, data, project_id: int, user_id: int):
        calls.append({"data": data, "project_id": project_id, "user_id": user_id})
        return SimpleNamespace(id=100 + len(calls))

    monkeypatch.setattr(campaign_service.execution_service, "create_run", fake_create_run)
    runs = start_campaign(
        db_session, project_id=1, campaign_id=campaign.id, user_id=9
    )

    assert [run.id for run in runs] == [101, 102]
    assert [call["data"]["scenario_id"] for call in calls] == [10, 10]
    assert {call["data"]["trigger_type"] for call in calls} == {"CAMPAIGN"}
    assert {call["project_id"] for call in calls} == {1}
    assert {call["user_id"] for call in calls} == {9}
    db_session.refresh(campaign)
    assert campaign.status == "running"


def test_start_campaign_rejects_cross_project_access(db_session) -> None:
    campaign = _campaign(db_session, project_id=2)
    _item(db_session, campaign.id, 1)
    db_session.commit()

    with pytest.raises(APIException) as exc:
        start_campaign(db_session, project_id=1, campaign_id=campaign.id, user_id=9)

    assert exc.value.http_status == 404


def test_start_campaign_rejects_empty_campaign(db_session) -> None:
    campaign = _campaign(db_session)
    db_session.commit()

    with pytest.raises(APIException) as exc:
        start_campaign(db_session, project_id=1, campaign_id=campaign.id, user_id=9)

    assert exc.value.http_status == 400

def test_campaign_run_api_returns_canonical_run_ids(
    client, db_session, auth_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _campaign(db_session)
    db_session.commit()
    import app.modules.campaign_execution.router as campaign_router

    monkeypatch.setattr(
        campaign_router,
        "start_campaign",
        lambda db, project_id, campaign_id, user_id: [SimpleNamespace(id=501), SimpleNamespace(id=502)],
    )

    response = client.post(
        f"/api/v1/execution/campaigns/{campaign.id}/runs", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"campaign_id": campaign.id, "run_ids": [501, 502]}
