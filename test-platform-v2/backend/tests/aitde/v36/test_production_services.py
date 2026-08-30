"""AITDE V3.6 production services validation (V36-001..V36-012 task gates).

These unit tests exercise the security-critical invariants that the V3.6 plan
§11 / §93 mandates: production write is blocked, everything is audited and
sanitised, masking is non-reversible yet relation-preserving, and AI output only
ever produces Proposals (never an auto-verified PASS).
"""
from __future__ import annotations

import json

import pytest

from app.modules.aitde.common.enums import PolicyDecision
from app.modules.aitde.production import repository as repo
from app.modules.aitde.production import services
from app.modules.aitde.production.policies import (
    ProdRoWorkerProfile,
    production_db_guard,
    prod_ro_worker_profile,
    readonly_browser_policy,
)


# ── V36-001: PROD_RO worker profile ─────────────────────────────────────────
def test_v36_001_prod_ro_worker_rejects_write_capability():
    ok, reason = prod_ro_worker_profile.validate(
        network_zone="PROD_RO", capabilities=["MYSQL", "BROWSER"]
    )
    assert ok is False
    assert "write capability" in reason


def test_v36_001_prod_ro_worker_readonly_ok():
    ok, _ = prod_ro_worker_profile.validate(
        network_zone="PROD_RO", capabilities=["BROWSER", "HTTP"]
    )
    assert ok is True
    resolved = prod_ro_worker_profile.resolve(
        network_zone="PROD_RO", capabilities=["BROWSER", "HTTP"]
    )
    assert resolved["policy_profile"] == "prod_ro"
    assert resolved["secret_scope"] == "prod_ro"


def test_v36_001_non_prod_ro_not_restricted():
    ok, _ = prod_ro_worker_profile.validate(
        network_zone="TEST", capabilities=["MYSQL"]
    )
    assert ok is True


# ── V36-002: persistent observation session ────────────────────────────────
def test_v36_002_observation_session_lifecycle(db):
    sid = services.production_observer_service.start(
        db, project_id=1, environment_id=2, mission_id=3, worker_id=4,
        mode="OBSERVE", started_by=9,
    )
    assert sid > 0
    state = services.production_observer_service.status(db, sid)
    assert state["status"] == "ACTIVE"
    assert state["mode"] == "OBSERVE"
    services.production_observer_service.stop(db, sid, user_id=9)
    assert services.production_observer_service.status(db, sid)["status"] == "FINISHED"


def test_v36_002_recover_after_restart(db):
    sid = services.production_observer_service.start(
        db, project_id=1, environment_id=2, mission_id=None, worker_id=None,
        mode="READONLY_EXPLORE", started_by=9,
    )
    recovered = services.production_observer_service.recover_after_restart(db)
    assert recovered >= 1
    assert services.production_observer_service.status(db, sid)["status"] == "FINISHED"


# ── V36-003: read-only browser guard ────────────────────────────────────────
def test_v36_003_browser_denies_write():
    decision, _ = readonly_browser_policy.evaluate(url="https://prod/pay/order", method="POST")
    assert decision == PolicyDecision.DENY.value
    decision, _ = readonly_browser_policy.evaluate(semantic_action="click_refund")
    assert decision == PolicyDecision.DENY.value


def test_v36_003_browser_allows_navigation():
    decision, _ = readonly_browser_policy.evaluate(url="https://prod/news", method="GET")
    assert decision == PolicyDecision.ALLOW.value


def test_v36_003_browser_whitelisted_readonly_post():
    decision, _ = readonly_browser_policy.evaluate(url="https://prod/ee/search/q", method="POST")
    assert decision == PolicyDecision.ALLOW.value


# ── V36-004: XHR evidence upgrades (sanitizer + persistent) ────────────────
def test_v36_004_xhr_redacts_auth_cookie(db):
    services.xhr_evidence_service.set_base_url("https://prod.example")
    sid = services.production_observer_service.start(
        db, project_id=1, environment_id=2, mission_id=None, worker_id=None,
        mode="OBSERVE", started_by=9,
    )
    journey_id = services.xhr_evidence_service.capture(
        db,
        session_id=sid,
        project_id=1,
        journey_name="login-journey",
        events=[
            {
                "event_type": "XHR",
                "method": "POST",
                "url": "/login",
                "headers": {"Authorization": "Bearer abc", "Cookie": "sid=1", "X-Request": "x"},
                "body": '{"username":"a","password":"secret"}',
                "content_type": "application/json",
            }
        ],
    )
    steps = repo.list_journey_steps(db, journey_id)
    xhr = json.loads(steps[0].xhr_refs_json)
    assert xhr["headers"]["Authorization"] == "<REDACTED>"
    assert xhr["headers"]["Cookie"] == "<REDACTED>"
    assert "secret" not in xhr["body"]
    assert "<REDACTED>" in xhr["body"]


# ── V36-005: prod DB guard ──────────────────────────────────────────────────
def test_v36_005_db_guard_rejects_writes():
    for sql in ["DELETE FROM t", "UPDATE t SET x=1", "DROP TABLE t", "CREATE TABLE t(id int)",
                "INSERT INTO t VALUES (1)", "; SELECT 1; DROP TABLE t"]:
        ok, _ = production_db_guard.validate(sql)
        assert ok is False, sql


def test_v36_005_db_guard_rejects_cte():
    ok, _ = production_db_guard.validate("WITH x AS (SELECT 1) SELECT * FROM x")
    assert ok is False


def test_v36_005_db_guard_allows_select():
    ok, reason = production_db_guard.validate("SELECT * FROM users WHERE id=1")
    assert ok is True, reason


def test_v36_005_db_guard_schema_allowlist():
    from app.modules.aitde.production.policies import ProductionDbGuard

    guard = ProductionDbGuard(schema_allowlist=["users"])
    ok, _ = guard.guard_scan("SELECT * FROM users", ["users"])
    assert ok is True
    ok, _ = guard.guard_scan("SELECT * FROM secrets", ["secrets"])
    assert ok is False
    # Default singleton has an empty allowlist (no restriction at this layer).
    ok, _ = production_db_guard.guard_scan("SELECT * FROM anything", ["anything"])
    assert ok is True


# ── V36-006: query audit 100% coverage ─────────────────────────────────────
def test_v36_006_query_audit_records_allow(db):
    out = services.production_db_explorer.inspect(
        db, project_id=1, data_source_id=5, session_id=None,
        sql="SELECT * FROM users", schema="public", table_names=["users"],
        row_provider=lambda sql: [{"id": 1}],
    )
    assert out["row_count"] == 1
    audits = repo.list_query_audits(db, 1)
    assert len(audits) == 1
    assert audits[0].policy_decision == "ALLOW"


def test_v36_006_query_audit_records_deny(db):
    with pytest.raises(Exception):
        services.production_db_explorer.inspect(
            db, project_id=1, data_source_id=5, session_id=None,
            sql="DELETE FROM users", schema="public", table_names=["users"],
        )
    audits = repo.list_query_audits(db, 1)
    assert len(audits) == 1
    assert audits[0].policy_decision == "DENY"


# ── V36-007: PII classifier ─────────────────────────────────────────────────
def test_v36_007_pii_classifier():
    assert services.pii_classifier.classify("email", "a@b.com") == "EMAIL"
    assert services.pii_classifier.classify("mobile", "13800138000") == "PHONE"
    assert services.pii_classifier.classify("idcard", "11010119900101123X") == "ID_NUMBER"
    assert services.pii_classifier.classify("notes", "hello world") == "FREE_TEXT"


# ── V36-008: masking (deterministic token, relation-preserving) ────────────
def test_v36_008_masking_deterministic_token_keeps_relation():
    from app.models.production_evidence import MaskingRule

    rules = [MaskingRule(profile_id=1, field_pattern="user_id", strategy="TOKENIZE", priority=10)]
    r1 = services.masking_service.apply(profile_id=1, rules=rules, record={"user_id": "42"})
    r2 = services.masking_service.apply(profile_id=1, rules=rules, record={"user_id": "42"})
    assert r1["user_id"] == r2["user_id"]
    assert r1["user_id"] != "42"


def test_v36_008_masking_redacts_token_field():
    from app.models.production_evidence import MaskingRule

    rules = [MaskingRule(profile_id=1, field_pattern="token", strategy="REDACT", priority=10)]
    out = services.masking_service.apply(profile_id=1, rules=rules, record={"token": "abc"})
    assert out["token"] == "<REDACTED>"


# ── V36-009: entity graph extractor (depth / cycle / row caps) ──────────────
def test_v36_009_entity_graph_cycle_cap():
    loader = lambda etype, ref, depth: (  # noqa: E731
        [{"entity_type": "user", "ref_hash": "1", "relation": "FK"}] if ref != "1" else []
    )
    graph, h = services.entity_graph_extractor.extract(
        root_entity_type="order", root_ref_hash="1", child_loader=loader
    )
    # Must terminate (cycle-safe), bounded node count.
    assert len(graph["nodes"]) >= 1
    assert len(graph["nodes"]) <= services.entity_graph_extractor.max_nodes


# ── V36-010: template builder (no raw PII) ──────────────────────────────────
def test_v36_010_template_builder_masks(graph_for_template):
    template = services.prod_template_builder.build(
        name="tpl", graph=graph_for_template, masking_profile_id=1,
        rules=[], project_id=1, mission_id=None, created_by=9,
    )
    assert template["nodes"]
    # Raw PII VALUES must never survive (field keys may remain).
    assert "11010119900101123X" not in json.dumps(template, ensure_ascii=False)
    assert "a@b.com" not in json.dumps(template, ensure_ascii=False)


@pytest.fixture()
def graph_for_template():
    return {
        "root": "user:1",
        "nodes": [
            {"entity_type": "user", "ref_hash": "1", "depth": 0,
             "attributes": {"email": "a@b.com", "id_card": "11010119900101123X"}},
        ],
        "edges": [],
    }


# ── V36-011: template materializer (fixture + id remap) ────────────────────
def test_v36_011_template_materializer(db, template_row):
    mid = services.template_materializer.materialize(
        db, template_id=template_row.id, target_environment_id=6, project_id=1
    )
    assert mid > 0
    mat = repo.get_materialization(db, mid)
    assert mat.status == "READY"
    assert mat.fixture_id


@pytest.fixture()
def template_row(db):
    template = {"name": "t", "nodes": [
        {"entity_type": "user", "ref_hash": "42", "depth": 0, "attributes": {"email": "x@y.com"}},
    ], "edges": []}
    row = repo.create_prod_template(
        db, {"project_id": 1, "name": "t", "template_json": json.dumps(template), "validation_status": "VALID"}
    )
    return row


# ── V36-012: evidence gap analysis (never auto-approve) ────────────────────
def test_v36_012_gap_analysis_not_auto_approved():
    journey = {
        "events": [
            {"url": "/news", "semantic_action": {"name": "view_news"}},
            {"url": "/pay", "semantic_action": {"name": "click_pay"}},
        ]
    }
    proposals = services.production_evidence_to_design_service.analyze_gaps(
        journey=journey, contract_refs=["view_news"]
    )
    for p in proposals:
        assert p.get("auto_approved", False) is False
    kinds = [p["kind"] for p in proposals]
    assert "SCENARIO_GAP" in kinds


# ── ── ProdRoWorkerProfile import sanity ────────────────────────────────────
def test_prod_ro_profile_importable():
    assert ProdRoWorkerProfile is not None
