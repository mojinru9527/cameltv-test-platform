"""Data strategy policy tests (V32-005..V32-008)."""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.data.models import DataRequirement, DataSource
from app.modules.aitde.data.strategies import get_builder
from app.modules.aitde.data.strategies.api_builder import ApiDataBuilder
from app.modules.aitde.data.strategies.db_fixture_builder import DbFixtureBuilder
from app.modules.aitde.data.strategies.existing_finder import ExistingDataFinder
from app.modules.aitde.data.strategies.workflow_builder import WorkflowDataBuilder


def _req(db, entity="membership", constraints=None):
    r = DataRequirement(
        scenario_version_id=1,
        requirement_key=f"data-{entity}",
        entity_type=entity,
        constraints_json=json.dumps(constraints or {"status": "EXPIRED"}, ensure_ascii=False),
    )
    db.add(r)
    db.flush()
    return r


def _src(db, source_type, access_mode="READONLY", config=None):
    s = DataSource(
        project_id=1, source_type=source_type, name="s", access_mode=access_mode,
        config_json=json.dumps(config or {}, ensure_ascii=False), created_by=9,
    )
    db.add(s)
    db.flush()
    return s


def test_existing_finder_requires_readonly(db):
    req = _req(db)
    src = _src(db, "POSTGRES", access_mode="READWRITE")
    with pytest.raises(APIException) as exc:
        ExistingDataFinder().build(src, req, None, 1)
    assert exc.value.http_status == 400
    src.access_mode = "READONLY"
    db.flush()
    result = ExistingDataFinder().build(src, req, None, 1)
    assert len(result.entities) == 1
    assert result.entities[0].created_by_fixture is False


def test_db_fixture_builder_allowlist_enforced(db):
    req = _req(db, entity="membership")
    src = _src(db, "MYSQL", access_mode="READWRITE", config={"table_allowlist": ["user"]})
    with pytest.raises(APIException) as exc:
        DbFixtureBuilder().build(src, req, None, 1)
    assert exc.value.http_status == 400
    src.config_json = json.dumps({"table_allowlist": ["membership"]}, ensure_ascii=False)
    db.flush()
    result = DbFixtureBuilder().build(src, req, None, 1)
    assert result.entities[0].created_by_fixture is True
    assert result.entities[0].cleanup_action["action"] == "delete"


def test_api_builder_needs_environment_and_endpoint(db):
    req = _req(db)
    src = _src(db, "API", config={"create_endpoint": "/members"})
    with pytest.raises(APIException) as exc:
        ApiDataBuilder().build(src, req, None, 1)
    assert exc.value.http_status == 400
    result = ApiDataBuilder().build(src, req, 100, 1)
    assert result.entities[0].physical_ref["kind"] == "api_create"


def test_workflow_builder_is_interface_no_browser(db):
    req = _req(db)
    result = WorkflowDataBuilder().build(None, req, 200, 1)
    assert result.entities[0].physical_ref["kind"] == "workflow"
    assert result.risk_note == "workflow"


def test_get_builder_registry(db):
    assert isinstance(get_builder("DB_FIXTURE"), DbFixtureBuilder)
    assert isinstance(get_builder("EXISTING"), ExistingDataFinder)
    with pytest.raises(KeyError):
        get_builder("UNKNOWN")
