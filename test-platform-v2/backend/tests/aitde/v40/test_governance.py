"""AITDE V4.0 (V40-011/012/014/015/017/018) enterprise governance tests."""

from __future__ import annotations

from app.modules.aitde.governance.service import (
    AcceptanceReportService,
    BackupVerificationService,
    CostLedgerService,
    DrTestService,
    EncryptionVerificationService,
    ModelPolicyService,
    PlatformReadinessEvaluator,
    RbacPolicyService,
    RetentionService,
    SsoService,
)


def test_retention_evaluate_lifecycle(db):
    r = RetentionService
    r.upsert(db, 1, "EVIDENCE", "CONFIDENTIAL", retention_days=30)
    assert r.evaluate(db, "EVIDENCE", "CONFIDENTIAL", 10)["action"] == "ARCHIVE"
    assert r.evaluate(db, "EVIDENCE", "CONFIDENTIAL", 40)["action"] == "DELETE"
    # No policy -> KEEP.
    assert r.evaluate(db, "LOG", "RESTRICTED", 999)["action"] == "KEEP"


def test_model_policy_routing_fail_closed(db):
    m = ModelPolicyService
    m.upsert(db, 1, "PUBLIC", ["deepseek"], ["deepseek-v4"], redaction_required=False)
    assert m.is_allowed(db, "deepseek", "deepseek-v4", "PUBLIC")["allowed"] is True
    assert m.is_allowed(db, "openai", "gpt-4", "PUBLIC")["allowed"] is False
    # Unconfigured sensitive level -> fail closed (no model).
    assert m.is_allowed(db, "deepseek", "deepseek-v4", "RESTRICTED")["allowed"] is False


def test_cost_ledger_and_budget(db):
    c = CostLedgerService
    c.record(db, 1, "SCENARIO_GEN", "deepseek-v4", input_units=100, output_units=50, cost_amount=1.5)
    c.record(db, 1, "TRIAGE", "deepseek-v4", input_units=40, output_units=10, cost_amount=0.5)
    usage = c.project_usage(db, 1)
    assert usage["entries"] == 2
    assert usage["total_cost"] == 2.0
    assert c.check_budget(db, 1, budget=1.0)["budget_exceeded"] is True
    assert c.check_budget(db, 1, budget=5.0)["budget_exceeded"] is False


def test_dr_test_record_and_list(db):
    d = DrTestService
    d.record(db, 1, "BACKUP_RESTORE", "test", "PASS", rto_seconds=120, rpo_seconds=60, evidence_uri="s3://dr/1")
    d.record(db, 1, "TEMPORAL_RECOVERY", "test", "FAIL", rto_seconds=999, rpo_seconds=999)
    rows = d.list(db, 1)
    assert len(rows) == 2
    assert rows[0]["test_type"] == "TEMPORAL_RECOVERY"  # newest first


def test_platform_readiness_gate_pass_and_fail():
    ev = PlatformReadinessEvaluator
    ok = {
        "p0_false_pass_rate": 0.005,
        "false_fail_rate": 0.01,
        "evidence_completeness": 0.995,
        "replay_audit_consistency": 0.995,
        "fixture_cleanup_success": 0.995,
        "prod_unauthorized_write": 0,
        "secret_leakage": 0,
        "pii_leakage": 0,
        "contract_unauthorized_mutation": 0,
        "mission_workflow_adoption": 0.85,
    }
    assert ev.evaluate(ok)["pass"] is True

    bad = dict(ok)
    bad["p0_false_pass_rate"] = 0.02  # exceeds <1%
    bad["prod_unauthorized_write"] = 1
    res = ev.evaluate(bad)
    assert res["pass"] is False
    assert "p0_false_pass_rate" in res["failed"]
    assert "prod_unauthorized_write" in res["failed"]


def test_platform_readiness_gate_missing_metric_fails():
    res = PlatformReadinessEvaluator.evaluate({"p0_false_pass_rate": 0.0})
    assert res["pass"] is False
    missing = [c["metric"] for c in res["checks"] if c.get("reason") == "missing"]
    assert len(missing) > 0


# ── V40-010 RBAC cross-project matrix ──────────────────────────────────────


def _grant_permission(db, user_id, project_id, code):
    from app.models.rbac import Permission, Role, RolePermission, UserRole

    role = Role(code=f"role-{project_id}-{user_id}", name="tester", data_scope="project")
    db.add(role)
    db.flush()
    perm = Permission(code=code, name=code, type="api")
    db.add(perm)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.add(UserRole(user_id=user_id, role_id=role.id, project_id=project_id))
    db.commit()
    return role


def test_rbac_cross_project_isolation(db):
    _grant_permission(db, user_id=1, project_id=10, code="mission:detail")
    assert RbacPolicyService.is_authorized(db, 1, 10, "mission:detail") is True
    # Role granted in project 10 must NOT authorize in project 20 (cross-project).
    assert RbacPolicyService.is_authorized(db, 1, 20, "mission:detail") is False
    assert RbacPolicyService.is_authorized(db, 1, 10, "mission:delete") is False
    assert RbacPolicyService.is_authorized(db, 2, 10, "mission:detail") is False


def test_rbac_cross_project_report_detects_leak(db):
    _grant_permission(db, user_id=1, project_id=10, code="mission:detail")
    report = RbacPolicyService.cross_project_report(db, 1, 10, [20, 30], "mission:detail")
    assert report["granted"] is True
    assert report["cross_project_leak"] == []
    assert report["pass"] is True


def _grant_wildcard(db, user_id, project_id):
    from app.models.rbac import Permission, Role, RolePermission, UserRole

    role = Role(code=f"role-super-{user_id}", name="super", data_scope="project")
    db.add(role)
    db.flush()
    perm = Permission(code="*", name="*", type="api")
    db.add(perm)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.add(UserRole(user_id=user_id, role_id=role.id, project_id=project_id))
    db.commit()


def test_rbac_wildcard_authorizes_everything(db):
    _grant_wildcard(db, user_id=3, project_id=10)
    # A super-admin role with the ``*`` permission authorizes any code in that project.
    assert RbacPolicyService.is_authorized(db, 3, 10, "mission:detail") is True
    assert RbacPolicyService.is_authorized(db, 3, 10, "contract:delete") is True
    # But the wildcard still does not leak across projects.
    assert RbacPolicyService.is_authorized(db, 3, 20, "mission:detail") is False


# ── V40-013 Encryption posture ──────────────────────────────────────────────


def test_encryption_verification_fails_when_disabled(monkeypatch):
    from app.core.config import settings

    for attr in ("db_encryption_enabled", "object_storage_encryption_enabled",
                 "use_external_secret_store", "https_only", "db_connection_tls"):
        monkeypatch.setattr(settings, attr, False)
    res = EncryptionVerificationService.verify()
    assert res["pass"] is False


def test_encryption_verification_passes_when_enabled(monkeypatch):
    from app.core.config import settings

    for attr in ("db_encryption_enabled", "object_storage_encryption_enabled",
                 "use_external_secret_store", "https_only", "db_connection_tls"):
        monkeypatch.setattr(settings, attr, True)
    res = EncryptionVerificationService.verify()
    assert res["pass"] is True
    assert len(res["checks"]) >= 5


# ── V40-020 Acceptance Report ───────────────────────────────────────────────


def test_acceptance_report_requires_traceability():
    inputs = {
        "mission": "m1", "contract_version": "v1", "scope_summary": {}, "scenario_coverage": {},
        "build_fingerprint": {"id": "b1"}, "p0_p1_outcomes": [], "quality_gate": {}, "false_pass_audit": [],
        "known_inconclusive": [], "defects": [], "evidence_links": [], "overrides": [], "approval": {},
    }
    res = AcceptanceReportService.build(inputs)
    assert res["valid"] is True
    assert res["report"]["build_fingerprint"] == {"id": "b1"}


def test_acceptance_report_rejects_missing_sections():
    res = AcceptanceReportService.build({"mission": "m1"})
    assert res["valid"] is False
    assert "contract_version" in res["missing"]
    assert "evidence_links" in res["missing"]


def test_acceptance_report_generate_aggregates_real_rows(db):
    from app.modules.aitde.contract.models import TestContract, TestContractVersion
    from app.modules.aitde.execution.models import ExecutionRun
    from app.modules.aitde.mission.models import Mission
    from app.modules.aitde.scenario.models import TestScenario

    mission = Mission(project_id=1, mission_key="M-REPORT-1", status="ACTIVE")
    db.add(mission)
    db.flush()
    scen = TestScenario(project_id=1, mission_id=mission.id, scenario_key="S-1", status="ACTIVE")
    db.add(scen)
    db.flush()
    contract = TestContract(mission_id=mission.id, name="c")
    db.add(contract)
    db.flush()
    db.add(TestContractVersion(contract_id=contract.id, version_no=1))
    db.add(ExecutionRun(project_id=1, mission_id=mission.id, scenario_id=scen.id, scenario_version_id=1, adapter_id=0, contract_version_id=0, outcome="PASS", runtime_status="COMPLETED"))
    db.add(ExecutionRun(project_id=1, mission_id=mission.id, scenario_id=scen.id, scenario_version_id=1, adapter_id=0, contract_version_id=0, outcome="BUSINESS_FAIL", runtime_status="COMPLETED"))
    db.commit()

    res = AcceptanceReportService.generate(db, mission.id)
    assert res["valid"] is True
    report = res["report"]
    assert report["scenario_coverage"]["scenarios"] == 1
    assert report["scenario_coverage"]["runs"] == 2
    assert report["p0_p1_outcomes"] == {"PASS": 1, "BUSINESS_FAIL": 1}
    assert len(report["evidence_links"]) == 2
    assert report["contract_version"]["version_no"] == 1


# ── V40-009 SSO scaffold ────────────────────────────────────────────────────


def test_sso_describe_and_group_mapping(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "sso_enabled", True)
    monkeypatch.setattr(settings, "sso_provider", "oidc")
    monkeypatch.setattr(settings, "sso_issuer", "https://idp.example")
    monkeypatch.setattr(settings, "sso_client_id", "cameltv")
    monkeypatch.setattr(settings, "sso_group_mapping", '{"qa-lead": "qa_lead"}')
    desc = SsoService.describe()
    assert desc["enabled"] is True
    assert desc["configured"] is True
    assert SsoService.resolve_role("qa-lead")["role"] == "qa_lead"
    assert SsoService.resolve_role("unknown")["mapped"] is False


# ── V40-016 HA/Backup readiness ─────────────────────────────────────────────


def test_backup_readiness_checklist(monkeypatch):
    from app.core.config import settings

    for attr, val in (
        ("storage_retention_enabled", True),
        ("object_storage_s3_bucket", "b"),
        ("temporal_enabled", True),
        ("use_external_secret_store", True),
    ):
        monkeypatch.setattr(settings, attr, val)
    assert BackupVerificationService.describe()["pass"] is True


def test_backup_restore_drill_records_dr_run(db):
    row = BackupVerificationService.record_restore_drill(db, 1, "test", "PASS", rto=90, rpo=45)
    assert row["status"] == "PASS"
    assert row["test_type"] == "OBJECT_STORE_RESTORE"
    assert row["rto_seconds"] == 90
