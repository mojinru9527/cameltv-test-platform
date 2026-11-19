"""V16-014-R2 验收：Case Catalog 将 A5 影响映射进 Mandatory Scope。"""
from __future__ import annotations

import pytest

from app.aiqe.models.case_catalog import CaseCatalogEntry
from app.aiqe.services.case_catalog import (
    CaseCatalogError,
    analysis_checksum,
    match_impact,
    upsert_entry,
    verify_analysis,
)
from app.aiqe.services.change_impact import analyze_change_impact
from app.aiqe.services.regression_service import (
    create_regression_request,
    record_deployment_attestation,
)
from app.aiqe.services.run_launch import launch
from app.aiqe.services.snapshot_service import ensure_snapshot
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.defect import Defect
from app.models.project import Project

BASE = "a" * 40
HEAD = "b" * 40
SHA = "c" * 40

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "login",
            "driver": "http",
            "depends_on": [],
            "input": {"url": "https://api.test/login", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "login_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-LOGIN",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "order",
            "driver": "http",
            "depends_on": ["login"],
            "input": {"url": "https://api.test/orders", "expected_status": 201},
            "assertions": [
                {
                    "assertion_key": "order_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-ORDER",
                    "type": "http_status",
                    "expected": 201,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "verify",
            "driver": "http",
            "depends_on": ["order"],
            "input": {"url": "https://api.test/state", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "verify_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-VERIFY",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
    ],
    "edges": [{"from": "login", "to": "order"}, {"from": "order", "to": "verify"}],
}


def _project(db) -> None:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="CAT", name="Catalog", owner_id=1, status=1))
        db.flush()


def _impact(*, route: str = "/orders", file: str = "app/api/orders.py"):
    diff = (
        f"diff --git a/{file} b/{file}\n--- a/{file}\n+++ b/{file}\n"
        f'@@ -1 +1,3 @@\n+@router.post("{route}")\n+def create_order():\n'
    )
    return analyze_change_impact(
        base_sha=BASE, head_sha=HEAD, changed_files=[file], diff_text=diff
    )


def _catalog(db):
    _project(db)
    return upsert_entry(
        db,
        project_id=1,
        case_id="CASE-ORDER-1",
        node_key="order",
        route="/orders",
        file_path="app/api/orders.py",
        symbol="create_order",
    )


def _source_run(db):
    from app.aiqe.services.capability_registry import register_manifest

    _project(db)
    register_manifest(
        db,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    workflow = create_workflow(db, project_id=1, graph=GRAPH)
    approve_workflow(db, workflow.id, approved_by=1)
    ensure_snapshot(db, workflow)
    result = launch(
        db,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="catalog-src",
    )
    from sqlalchemy import select

    from app.aiqe.models.run import NodeRun

    node = db.scalar(select(NodeRun).where(NodeRun.run_id == result.run_id))
    node.status = "FAILED"
    db.commit()
    return db.get(__import__("app.aiqe.models.run", fromlist=["TestRun"]).TestRun, result.run_id)


def test_catalog_match_route_to_node_refs(db_session):
    _catalog(db_session)
    matched = match_impact(
        db_session, project_id=1, impact_analysis=_impact(), allowed_node_keys=["login", "order"]
    )
    assert matched["node_refs"] == ["node:order"]
    assert matched["matched_case_ids"] == ["CASE-ORDER-1"]
    assert matched["unknown_broadened"] is False


def test_unknown_analysis_broadens_to_all_catalog_nodes(db_session):
    _catalog(db_session)
    upsert_entry(
        db_session,
        project_id=1,
        case_id="CASE-LOGIN",
        node_key="login",
        route="/login",
    )
    unknown = {"status": "UNKNOWN", "evidence": [], "checksum": ""}
    matched = match_impact(
        db_session,
        project_id=1,
        impact_analysis=unknown,
        allowed_node_keys=["login", "order", "verify"],
    )
    assert matched["unknown_broadened"] is True
    assert set(matched["node_refs"]) == {"node:login", "node:order"}


def test_catalog_checksum_and_project_isolation(db_session):
    _project(db_session)
    entry = _catalog(db_session)
    analysis = _impact()
    verify_analysis(analysis)
    tampered = dict(analysis)
    tampered["changed_files"] = ["other.py"]
    with pytest.raises(CaseCatalogError):
        verify_analysis(tampered)
    with pytest.raises(CaseCatalogError):
        verify_analysis({"status": "OK"})
    # 跨项目不可见
    from app.models.project import Project as P

    db_session.add(P(id=2, code="P2", name="P2", owner_id=1, status=1))
    db_session.flush()
    assert match_impact(db_session, project_id=2, impact_analysis=analysis)["node_refs"] == []
    assert entry.project_id == 1
    # upsert 更新而非重复
    again = upsert_entry(
        db_session,
        project_id=1,
        case_id="CASE-ORDER-1",
        node_key="order",
        route="/orders/v2",
    )
    assert again.id == entry.id
    assert len(list(db_session.query(CaseCatalogEntry))) == 1


def test_regression_includes_catalog_node_in_mandatory_scope(db_session):
    _catalog(db_session)
    source = _source_run(db_session)
    defect = Defect(project_id=1, defect_id="BUG-CAT", title="x", severity="P1", status="open")
    db_session.add(defect)
    db_session.flush()
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=SHA, source="ci"
    )
    db_session.commit()
    analysis = _impact()
    row, run, created = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=SHA,
        source_run_id=source.id,
        idempotency_key="catalog-reg",
        impact_analysis=analysis,
    )
    db_session.commit()
    assert created is True and run is not None
    from app.aiqe.models.regression_scope import RegressionScopeSnapshot

    scope = db_session.get(RegressionScopeSnapshot, row.scope_snapshot_id)
    mandatory = set(scope.mandatory_node_keys_json or [])
    assert {"login", "order"}.issubset(mandatory)
    assert run.environment_snapshot_json["impact_analysis"]["checksum"] == analysis["checksum"]
    assert run.environment_snapshot_json["impact_analysis"]["catalog_size"] == 1


def test_tampered_impact_analysis_blocks_regression(db_session):
    _catalog(db_session)
    source = _source_run(db_session)
    defect = Defect(project_id=1, defect_id="BUG-CAT2", title="x", severity="P1", status="open")
    db_session.add(defect)
    db_session.flush()
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=SHA, source="ci"
    )
    db_session.commit()
    analysis = dict(_impact())
    analysis["changed_files"] = ["tampered.py"]  # checksum 不再匹配
    row, run, created = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=SHA,
        source_run_id=source.id,
        idempotency_key="catalog-reg-bad",
        impact_analysis=analysis,
    )
    db_session.commit()
    assert created is True
    assert run is None
    assert row.status == "BLOCKED"
    assert any(item["code"] == "IMPACT_ANALYSIS_INVALID" for item in (row.blockers_json or []))
