"""AITDE V3.7 lineage service + backfill tests (V37-001/002)."""

from __future__ import annotations

from app.modules.aitde.common.enums import LineageEdgeType, LineageNodeType
from app.modules.aitde.scenario.models import (
    TestOracle,
    TestScenario,
    TestScenarioVersion,
)
from app.modules.aitde.scope.models import ScopeItem
from app.modules.aitde.smart_regression import service
from app.modules.aitde.sources.models import SourceArtifact, SourceFragment


def test_add_edge_idempotent(db):
    first = service.LineageService.add_edge(
        db,
        1,
        7,
        LineageNodeType.SCENARIO.value,
        1,
        LineageNodeType.SCENARIO_VERSION.value,
        2,
        LineageEdgeType.BINDS.value,
    )
    second = service.LineageService.add_edge(
        db,
        1,
        7,
        LineageNodeType.SCENARIO.value,
        1,
        LineageNodeType.SCENARIO_VERSION.value,
        2,
        LineageEdgeType.BINDS.value,
    )
    assert first is not None
    assert second is None  # duplicate -> not re-inserted
    assert len(service.lineage_list(db, 1, 7)["edges"]) == 1


def test_dangling_edge_detected(db):
    service.LineageService.add_edge(
        db,
        1,
        7,
        LineageNodeType.SCENARIO.value,
        999,
        LineageNodeType.SCENARIO_VERSION.value,
        888,
        LineageEdgeType.BINDS.value,
    )
    dangling = service.lineage_dangling(db, 1, 7)["dangling"]
    assert len(dangling) == 1
    assert dangling[0]["to"] == "SCENARIO_VERSION:888"


def test_node_with_no_outgoing_edge_is_not_dangling(db):
    db.add(TestScenario(id=1, project_id=1, mission_id=7, scenario_key="SC1"))
    db.add(
        TestScenarioVersion(id=2, scenario_id=1, version_no=1, contract_version_id=0)
    )
    db.flush()
    service.LineageService.add_edge(
        db,
        1,
        7,
        LineageNodeType.SCENARIO.value,
        1,
        LineageNodeType.SCENARIO_VERSION.value,
        2,
        LineageEdgeType.BINDS.value,
    )
    dangling = service.lineage_dangling(db, 1, 7)["dangling"]
    assert dangling == []  # all referenced nodes exist


def test_find_paths_to_scenarios(db):
    service.LineageService.add_edge(
        db,
        1,
        7,
        LineageNodeType.SOURCE_FRAGMENT.value,
        10,
        LineageNodeType.SCENARIO.value,
        3,
        LineageEdgeType.APPLIES_TO.value,
    )
    service.LineageService.add_edge(
        db,
        1,
        7,
        LineageNodeType.SCENARIO.value,
        3,
        LineageNodeType.SCENARIO_VERSION.value,
        4,
        LineageEdgeType.BINDS.value,
    )
    paths = service.LineageService.find_paths_to_scenarios(
        db, 1, 7, LineageNodeType.SOURCE_FRAGMENT.value, 10
    )
    assert len(paths) == 2  # reaches both SCENARIO:3 and SCENARIO_VERSION:4
    assert any(
        p["type"] == LineageNodeType.SCENARIO_VERSION.value
        and p["path"][-1] == "SCENARIO_VERSION:4"
        for p in paths
    )


def test_backfill_builds_and_is_idempotent(db):
    artifact = SourceArtifact(project_id=1, source_type="REQUIREMENT", name="PRD")
    db.add(artifact)
    db.flush()
    frag = SourceFragment(artifact_id=artifact.id, fragment_key="f1", content_hash="a")
    scope = ScopeItem(
        mission_id=7,
        scope_key="s1",
        source_refs_json='[{"type":"SOURCE_FRAGMENT","id":1}]',
    )
    db.add_all([frag, scope])
    db.flush()

    scenario = TestScenario(project_id=1, mission_id=7, scenario_key="SC1")
    db.add(scenario)
    db.flush()
    version = TestScenarioVersion(
        scenario_id=scenario.id,
        version_no=1,
        risk_level="P0",
        contract_version_id=0,
        source_refs_json="[]",
    )
    db.add(version)
    db.flush()
    db.add(TestOracle(scenario_version_id=version.id, oracle_key="o1"))
    db.flush()

    out1 = service.LineageBackfillService.backfill(db, 1, 7)
    out2 = service.LineageBackfillService.backfill(db, 1, 7)
    assert out1["created_edges"] > 0
    assert out2["created_edges"] == 0  # idempotent: no new edges on re-run
    edges = service.lineage_list(db, 1, 7)["edges"]
    types = {(e["from_type"], e["to_type"]) for e in edges}
    assert (
        LineageNodeType.SCENARIO.value,
        LineageNodeType.SCENARIO_VERSION.value,
    ) in types
    assert (
        LineageNodeType.SCENARIO_VERSION.value,
        LineageNodeType.ORACLE.value,
    ) in types
