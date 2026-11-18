"""AUD-016 / AUD-012：Evidence 引用服务端校验 + 可复现缺陷草稿验收测试。

对应 v1.5 §03 AUD-016「验收」与 §02 AUD-012「完成标准」：
- Agent/草稿返回不存在或跨项目 evidence ref 时，整个结果验证失败；
- 缺陷必须关联失败断言，或说明为什么没有断言；
- 复现包不得包含真实 Secret，且包含 Workflow/Fixture/Environment/Artifact 引用；
- 人工确认后才转正式缺陷，保留 draft 审计。
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.services.defect_draft_service import (
    DefectDraftError,
    build_bundle,
    build_defect_draft,
    promote_draft,
)
from app.aiqe.services.evidence_service import (
    EvidenceRefError,
    parse_ref,
    resolve_evidence_refs,
)
from app.models.defect import Defect
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

CANARY = "CANARY_SECRET_repro_42"


def _seed_project(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="repro", password="x", nickname="R", email="r@r.local", status=1)
    db.add_all(
        [
            user,
            Project(id=1, code="repro-p1", name="P1", owner_id=1, status=1),
            Project(id=2, code="repro-p2", name="P2", owner_id=2, status=1),
        ]
    )
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


def _client(db: Session) -> TestClient:
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _db():
        yield db

    def _user() -> CurrentUser:
        perms = ["menu:aiqe_runs", "defect:list", "defect:update"]
        return CurrentUser(
            user=db.get(User, 1), permissions=perms, project_id=1, system_permissions=perms
        )

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def _run_with_failure(
    db: Session, *, key: str = "RUN-REPRO-1", project_id: int = 1
) -> tuple[TestRun, NodeRun, StepAttempt, RunAssertionResult]:
    run = TestRun(
        project_id=project_id,
        run_key=key,
        source_type="manual",
        status="COMPLETED",
        outcome="FAIL",
        commit_sha="c" * 40,
        build_ref="build-7",
        environment_snapshot_json={"fixture_namespace": "aiqe-run-1", "env": "test"},
    )
    db.add(run)
    db.flush()
    node = NodeRun(
        run_id=run.id,
        node_key="ui",
        driver_key="playwright",
        status="FAILED",
        input_ref={"url": "https://cameltv.test/live", "action": "click"},
    )
    db.add(node)
    db.flush()
    attempt = StepAttempt(node_run_id=node.id, step_key="ui", attempt_no=1, status="FAILED")
    db.add(attempt)
    db.flush()
    assertion = RunAssertionResult(
        step_attempt_id=attempt.id,
        assertion_key="live.entry",
        assertion_type="exists",
        status="FAIL",
        expected_json=True,
        actual_json=False,
        required=True,
        source_ref="dom:#live-entry",
    )
    db.add(assertion)
    db.commit()
    return run, node, attempt, assertion


def _event(db: Session, run: TestRun) -> str:
    from app.aiqe.services.event_service import append_event

    event, _ = append_event(
        db,
        run_id=run.id,
        event_type="node.failed",
        payload={"schema_version": "1.0", "node_key": "ui"},
        producer="system",
    )
    db.commit()
    return event.id


# ── 1. Evidence Ref 解析 ─────────────────────────────────
def test_parse_ref_rejects_unknown_prefix():
    with pytest.raises(EvidenceRefError):
        parse_ref("https://evil.example/artifact")
    with pytest.raises(EvidenceRefError):
        parse_ref("artifact:")


def test_resolves_existing_refs_in_scope(db_session):
    run, node, attempt, assertion = _run_with_failure(db_session)
    event_id = _event(db_session, run)
    refs = [
        f"node:{node.id}",
        f"attempt:{attempt.id}",
        f"assertion:{attempt.id}:live.entry",
        f"event:{event_id}",
        f"run:{run.id}",
        "signal:ui_overlay_hit_target",
    ]
    resolved = resolve_evidence_refs(db_session, project_id=1, run_id=run.id, refs=refs)
    assert {item.kind for item in resolved} == {
        "node",
        "attempt",
        "assertion",
        "event",
        "run",
        "signal",
    }
    signal = next(item for item in resolved if item.kind == "signal")
    assert signal.metadata["format_only"] is True


def test_nonexistent_ref_fails_whole_result(db_session):
    run, _node, _attempt, _assertion = _run_with_failure(db_session)
    with pytest.raises(EvidenceRefError) as excinfo:
        resolve_evidence_refs(
            db_session,
            project_id=1,
            run_id=run.id,
            refs=[f"artifact:{'0' * 36}"],
        )
    assert excinfo.value.code == "EVIDENCE_REF_INVALID"


def test_cross_project_and_other_run_refs_fail(db_session):
    run, node, _attempt, _assertion = _run_with_failure(db_session)
    other_run = TestRun(project_id=1, run_key="RUN-OTHER", status="COMPLETED")
    db_session.add(other_run)
    db_session.commit()
    with pytest.raises(EvidenceRefError):
        # node 属于 run，但请求声明的是另一个 Run
        resolve_evidence_refs(
            db_session, project_id=1, run_id=other_run.id, refs=[f"node:{node.id}"]
        )
    with pytest.raises(EvidenceRefError):
        resolve_evidence_refs(
            db_session, project_id=2, run_id=run.id, refs=[f"node:{node.id}"]
        )


# ── 2. 缺陷草稿 ─────────────────────────────────────────
def test_draft_requires_failing_assertion_or_reason(db_session):
    run = TestRun(project_id=1, run_key="RUN-NO-ASSERT", status="COMPLETED", outcome="PASS")
    db_session.add(run)
    db_session.commit()
    with pytest.raises(DefectDraftError):
        build_defect_draft(db_session, project_id=1, run_id=run.id, title="无断言")
    draft = build_defect_draft(
        db_session,
        project_id=1,
        run_id=run.id,
        title="Runner 崩溃",
        no_assertion_reason="Runner process crashed before assertions",
    )
    assert draft.reproduction_status == "REPRODUCTION_INCOMPLETE"
    assert draft.is_draft is True


def test_draft_rejects_unresolvable_evidence(db_session):
    run, *_ = _run_with_failure(db_session)
    with pytest.raises(EvidenceRefError):
        build_defect_draft(
            db_session,
            project_id=1,
            run_id=run.id,
            title="带假证据",
            evidence_refs=["artifact:does-not-exist"],
        )


def test_draft_records_assertions_and_is_idempotent(db_session):
    run, node, _attempt, _assertion = _run_with_failure(db_session, key="RUN-REPRO-2")
    event_id = _event(db_session, run)
    draft = build_defect_draft(
        db_session,
        project_id=1,
        run_id=run.id,
        title="直播入口不可点",
        severity="P1",
        evidence_refs=[f"event:{event_id}", f"node:{node.id}"],
        node_run_id=node.id,
        correlation_id="corr-1",
    )
    assert draft.reproduction_status == "COMPLETE"
    assert draft.failing_assertion_refs_json
    assert draft.evidence_refs_json
    assert draft.draft_id == str(draft.id)

    again = build_defect_draft(
        db_session, project_id=1, run_id=run.id, title="直播入口不可点"
    )
    assert again.id == draft.id
    assert db_session.query(Defect).filter(Defect.is_draft.is_(True)).count() == 1


def test_draft_redacts_secrets(db_session):
    run, *_ = _run_with_failure(db_session, key="RUN-REPRO-3")
    draft = build_defect_draft(
        db_session,
        project_id=1,
        run_id=run.id,
        title="token 泄漏检查",
        description=f"login response access_token={CANARY}",
    )
    assert CANARY not in (draft.description or "")


# ── 3. 复现包 ───────────────────────────────────────────
def test_bundle_contains_required_sections_and_no_secret(db_session):
    run, node, attempt, _assertion = _run_with_failure(db_session, key="RUN-REPRO-4")
    event_id = _event(db_session, run)
    draft = build_defect_draft(
        db_session,
        project_id=1,
        run_id=run.id,
        title="复现包",
        evidence_refs=[f"event:{event_id}"],
        node_run_id=node.id,
    )
    bundle = build_bundle(db_session, project_id=1, defect=draft)
    payload = bundle.to_dict()
    assert payload["build_sha"] == "c" * 40
    assert payload["fixture_recipe"]["fixture_namespace"] == "aiqe-run-1"
    assert payload["environment_snapshot"]["environment_snapshot"]["env"] == "test"
    assert payload["steps"][0]["node_key"] == "ui"
    assert payload["assertions"][0]["status"] == "FAIL"
    assert payload["evidence"][0]["kind"] == "event"
    assert payload["commands"]
    assert CANARY not in json.dumps(payload, ensure_ascii=False)

    markdown = bundle.to_markdown()
    assert "## 复现步骤" in markdown and "## 失败断言" in markdown

    archive = zipfile.ZipFile(io.BytesIO(bundle.to_zip()))
    assert set(archive.namelist()) == {"reproduction-bundle.json", "reproduction.md"}


def test_bundle_requires_run(db_session):
    defect = Defect(project_id=1, title="无 Run", is_draft=True)
    db_session.add(defect)
    db_session.commit()
    with pytest.raises(DefectDraftError):
        build_bundle(db_session, project_id=1, defect=defect)


# ── 4. 人工确认 ─────────────────────────────────────────
def test_promote_draft_keeps_audit(db_session):
    run, *_ = _run_with_failure(db_session, key="RUN-REPRO-5")
    draft = build_defect_draft(db_session, project_id=1, run_id=run.id, title="确认审计")
    promoted = promote_draft(db_session, defect_id=draft.id, project_id=1, approver_id=9)
    assert promoted.is_draft is False
    assert promoted.approved_by == 9
    assert promoted.approved_at is not None
    assert promoted.draft_id == str(draft.id)
    with pytest.raises(DefectDraftError):
        promote_draft(db_session, defect_id=draft.id, project_id=1, approver_id=9)


# ── 5. API ──────────────────────────────────────────────
def test_api_draft_bundle_confirm_flow(db_session):
    _seed_project(db_session)
    run, node, _attempt, _assertion = _run_with_failure(db_session, key="RUN-REPRO-API")
    event_id = _event(db_session, run)
    client = _client(db_session)
    try:
        created = client.post(
            "/api/v1/aiqe/defects/drafts",
            json={
                "run_id": run.id,
                "title": "API 草稿",
                "severity": "P1",
                "evidence_refs": [f"event:{event_id}"],
                "node_run_id": node.id,
            },
        )
        assert created.status_code == 200, created.text
        data = created.json()["data"]
        assert data["is_draft"] is True
        assert data["reproduction_status"] == "COMPLETE"

        bundle = client.get(f"/api/v1/aiqe/defects/{data['id']}/reproduction-bundle")
        assert bundle.status_code == 200
        assert bundle.json()["data"]["bundle"]["build_sha"] == "c" * 40

        download = client.get(
            f"/api/v1/aiqe/defects/{data['id']}/reproduction-bundle/download"
        )
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"

        confirmed = client.post(f"/api/v1/aiqe/defects/{data['id']}/confirm")
        assert confirmed.status_code == 200
        assert confirmed.json()["data"]["is_draft"] is False
    finally:
        from app.main import app

        app.dependency_overrides.clear()


def test_api_rejects_invalid_evidence_and_cross_project(db_session):
    _seed_project(db_session)
    run, *_ = _run_with_failure(db_session, key="RUN-REPRO-API2")
    client = _client(db_session)
    try:
        bad = client.post(
            "/api/v1/aiqe/defects/drafts",
            json={
                "run_id": run.id,
                "title": "假证据",
                "evidence_refs": [f"artifact:{'0' * 36}"],
            },
        )
        assert bad.status_code == 422

        foreign = client.get("/api/v1/aiqe/defects/424242/reproduction-bundle")
        assert foreign.status_code == 404
    finally:
        from app.main import app

        app.dependency_overrides.clear()
