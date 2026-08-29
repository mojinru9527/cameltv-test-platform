"""AITDE V3.1 ScenarioAdapter service tests (V31-001)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import AdapterStatus, AdapterType
from app.modules.aitde.execution import adapter_registry


def _adapter_payload(scenario_graph, **overrides):
    data = {
        "scenario_version_id": scenario_graph["scenario_version"].id,
        "adapter_type": AdapterType.API.value,
        "config": {"base_url": "https://api.example.com"},
        "adapter_version": "1.0",
    }
    data.update(overrides)
    return data


def test_create_adapter_binds_version(db, scenario_graph):
    adapter = adapter_registry.create_adapter(
        db,
        scenario_graph["scenario"].id,
        _adapter_payload(scenario_graph),
        project_id=1,
        user_id=9,
    )
    assert adapter.scenario_id == scenario_graph["scenario"].id
    assert adapter.scenario_version_id == scenario_graph["scenario_version"].id
    assert adapter.adapter_type == AdapterType.API.value
    assert adapter.status == AdapterStatus.DRAFT.value


def test_create_adapter_rejects_cross_project_scenario(db, scenario_graph):
    with pytest.raises(APIException) as exc:
        adapter_registry.create_adapter(
            db,
            scenario_graph["scenario"].id,
            _adapter_payload(scenario_graph),
            project_id=2,
            user_id=9,
        )
    assert exc.value.http_status == 400


def test_create_adapter_rejects_version_mismatch(db, scenario_graph):
    payload = _adapter_payload(scenario_graph)
    payload["scenario_version_id"] = 9999
    with pytest.raises(APIException) as exc:
        adapter_registry.create_adapter(
            db, scenario_graph["scenario"].id, payload, project_id=1, user_id=9
        )
    assert exc.value.http_status == 400


def test_list_adapters_scoped(db, scenario_graph):
    adapter_registry.create_adapter(
        db,
        scenario_graph["scenario"].id,
        _adapter_payload(scenario_graph),
        project_id=1,
        user_id=9,
    )
    items = adapter_registry.list_adapters(db, scenario_graph["scenario"].id, project_id=1)
    assert len(items) == 1
