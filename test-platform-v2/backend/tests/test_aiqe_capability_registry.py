"""M2 / TA-015：Capability Registry 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.services import capability_registry as registry
from app.aiqe.services.workflow_validator import WorkflowValidationError, validate_workflow


def test_register_without_evidence_is_unavailable(db_session):
    row = registry.register_manifest(
        db_session, node_id="node-a", capabilities=["browser.chromium", "api.http"]
    )
    assert row.available is False
    assert registry.supports(db_session, "node-a", "browser.chromium") is False


def test_register_with_evidence_and_supports(db_session):
    registry.register_manifest(
        db_session,
        node_id="node-a",
        capabilities=["browser.chromium", "api.http"],
        evidence_ref="run-123",
    )
    assert registry.supports(db_session, "node-a", "browser.chromium") is True
    assert registry.supports(db_session, "node-a", "browser.webkit") is False


def test_node_without_webkit_not_selected(db_session):
    registry.register_manifest(
        db_session, node_id="chromium-only", capabilities=["browser.chromium"], evidence_ref="r1"
    )
    registry.register_manifest(
        db_session,
        node_id="full-node",
        capabilities=["browser.chromium", "browser.webkit"],
        evidence_ref="r2",
    )
    assert registry.select_nodes(db_session, ["browser.webkit"]) == ["full-node"]
    assert registry.select_nodes(db_session, ["browser.chromium"]) == [
        "chromium-only",
        "full-node",
    ]


def test_select_requires_all_capabilities(db_session):
    registry.register_manifest(
        db_session,
        node_id="n1",
        capabilities=["browser.chromium", "db.readonly"],
        evidence_ref="r1",
    )
    assert registry.select_nodes(db_session, ["browser.chromium", "db.readonly"]) == ["n1"]
    assert registry.select_nodes(db_session, ["browser.chromium", "browser.webkit"]) == []


def test_upsert_updates_single_row(db_session):
    registry.register_manifest(db_session, node_id="n1", capabilities=["api.http"], evidence_ref="r1")
    registry.register_manifest(
        db_session, node_id="n1", capabilities=["api.http", "browser.webkit"], evidence_ref="r2"
    )
    rows = db_session.query(NodeCapabilityManifest).filter_by(node_id="n1").all()
    assert len(rows) == 1
    assert "browser.webkit" in rows[0].capabilities_json


def test_record_evidence_flips_available(db_session):
    registry.register_manifest(db_session, node_id="n1", capabilities=["api.http"])
    assert registry.supports(db_session, "n1", "api.http") is False
    registry.record_evidence(db_session, "n1", "run-9")
    assert registry.supports(db_session, "n1", "api.http") is True


def test_invalid_inputs(db_session):
    with pytest.raises(registry.CapabilityError):
        registry.register_manifest(db_session, node_id="", capabilities=["api.http"])
    with pytest.raises(registry.CapabilityError):
        registry.register_manifest(db_session, node_id="n1", capabilities=[])
    with pytest.raises(registry.CapabilityError):
        registry.record_evidence(db_session, "missing", "r1")


def test_known_capabilities_drive_validator():
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "ui",
                "driver": "playwright",
                "capability": "browser.chromium",
                "depends_on": [],
            }
        ],
        "edges": [],
        "run_policy": {"max_parallel_nodes": 1},
    }
    validate_workflow(
        graph,
        registered_drivers={"playwright"},
        registered_capabilities=registry.known_capabilities(),
    )

    graph["nodes"][0]["capability"] = "browser.hologram"
    with pytest.raises(WorkflowValidationError):
        validate_workflow(
            graph,
            registered_drivers={"playwright"},
            registered_capabilities=registry.known_capabilities(),
        )
