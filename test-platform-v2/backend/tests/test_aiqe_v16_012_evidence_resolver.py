"""V16-012 验收：A4 Evidence Resolver 强制校验（通过 Agent Adapter 执行）。

要求：
- A4 必须在 Adapter 路径注入服务端 resolver；
- 每个 supporting/contradicting ref 必须存在、同 Project、同 Run、类型合法、
  checksum 可验证、未墓碑；
- resolver 缺失/异常/空/跨项目/跨 Run → BLOCKED INVALID_EVIDENCE，不得 COMPLETED。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.aiqe.agents.base import AgentEvidenceError, AgentSchemaError
from app.aiqe.agents.failure_triage_agent import FailureTriageAgent
from app.aiqe.agents.protocol import AgentContext, BaseAgentAdapter
from app.aiqe.models.artifact import ArtifactType, ArtifactUploadStatus, RunArtifact
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.services.evidence_resolver import (
    EvidenceResolverError,
    build_evidence_resolver,
)
from app.models.project import Project


def _project(db, project_id: int = 1) -> None:
    if db.get(Project, project_id) is None:
        db.add(
            Project(
                id=project_id,
                code=f"P{project_id}",
                name=f"Project {project_id}",
                owner_id=1,
                status=1,
            )
        )
        db.flush()


def _run(db, *, project_id: int = 1, key: str = "RUN-EV-1") -> TestRun:
    _project(db, project_id)
    run = TestRun(project_id=project_id, run_key=key, status="RUNNING")
    db.add(run)
    db.flush()
    node = NodeRun(run_id=run.id, node_key="ui", driver_key="http", status="FAILED")
    db.add(node)
    db.flush()
    attempt = StepAttempt(node_run_id=node.id, step_key="ui", attempt_no=1, status="FAILED")
    db.add(attempt)
    db.flush()
    assertion = RunAssertionResult(
        step_attempt_id=attempt.id,
        assertion_key="ui.visible",
        assertion_type="exists",
        status="FAIL",
        required=True,
    )
    db.add(assertion)
    db.flush()
    artifact = RunArtifact(
        project_id=project_id,
        run_id=run.id,
        node_run_id=node.id,
        step_attempt_id=attempt.id,
        artifact_type=ArtifactType.SCREENSHOT,
        storage_uri=f"artifact://{run.id}/shot.png",
        sha256="a" * 64,
        upload_status=ArtifactUploadStatus.AVAILABLE,
        redaction_status="clean",
        size_bytes=10,
    )
    db.add(artifact)
    db.flush()
    run._evidence_ids = {  # type: ignore[attr-defined]
        "assertion": assertion.id,
        "attempt": attempt.id,
        "artifact": artifact.id,
    }
    db.commit()
    return run


def _payload(refs: list[str]) -> dict:
    return {
        "execution_outcome": "FAIL",
        "attribution_status": "NEEDS_EXPERIMENT",
        "hypotheses": [
            {
                "classification": "PRODUCT_DEFECT",
                "summary": "浮层遮挡",
                "supporting_evidence": refs,
                "contradicting_evidence": [],
                "missing_evidence": ["hit-test"],
                "recommended_experiment": "E1",
                "confidence": None,
                "status": "PROPOSED",
            }
        ],
        "human_review_required": True,
        "auto_close_defect": False,
    }


def _agent(payload: dict) -> FailureTriageAgent:
    return FailureTriageAgent(lambda system, user: json.dumps(payload, ensure_ascii=False))


def _adapter() -> BaseAgentAdapter:
    return BaseAgentAdapter(_agent(_payload([])), key="A4")


def _execute(db, run, payload: dict, resolver=None):
    agent = _agent(payload)
    adapter = BaseAgentAdapter(agent, key="A4", version="1.0.0")
    context = AgentContext(
        project_id=int(run.project_id),
        run_id=run.id,
        evidence_resolver=resolver
        if resolver is not None
        else build_evidence_resolver(db, project_id=int(run.project_id), run_id=run.id),
    )
    return adapter.execute(context, "triage please")


# ── 1. 有效证据 PASS ───────────────────────────────────────
def test_valid_evidence_passes_through_adapter(db_session):
    run = _run(db_session)
    refs = [f"assertion:{run._evidence_ids['assertion']}", f"artifact:{run._evidence_ids['artifact']}"]
    result = _execute(db_session, run, _payload(refs))
    assert result.status == "COMPLETED", result.warnings
    assert result.output["hypotheses"][0]["confidence_band"] in {"MEDIUM", "HIGH", "LOW"}
    assert result.output["evidence_hash"].startswith("sha256:")
    snapshot = result.output["evidence_snapshot"]["浮层遮挡"]
    assert snapshot[f"artifact:{run._evidence_ids['artifact']}"]["checksum"] == "a" * 64


# ── 2. 无效引用全部 BLOCKED ────────────────────────────────
def test_missing_evidence_ref_blocks(db_session):
    run = _run(db_session, key="RUN-EV-2")
    result = _execute(db_session, run, _payload(["artifact:ghost"]))
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EVIDENCE"
    assert result.needs_human is True


def test_unknown_ref_type_blocks(db_session):
    run = _run(db_session, key="RUN-EV-3")
    result = _execute(db_session, run, _payload(["http://evil.example/x"]))
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EVIDENCE"


def test_cross_run_artifact_blocks(db_session):
    run = _run(db_session, key="RUN-EV-4")
    other = _run(db_session, key="RUN-EV-OTHER")
    result = _execute(
        db_session, run, _payload([f"artifact:{other._evidence_ids['artifact']}"])
    )
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EVIDENCE"


def test_tombstoned_artifact_blocks(db_session):
    run = _run(db_session, key="RUN-EV-5")
    from app.aiqe.models.artifact import RunArtifact as Artifact

    artifact = db_session.get(Artifact, run._evidence_ids["artifact"])
    artifact.deleted_at = datetime.now(UTC)
    db_session.commit()
    result = _execute(db_session, run, _payload([f"artifact:{artifact.id}"]))
    assert result.status == "BLOCKED"


def test_checksum_missing_blocks(db_session):
    run = _run(db_session, key="RUN-EV-6")
    from app.aiqe.models.artifact import RunArtifact as Artifact

    artifact = db_session.get(Artifact, run._evidence_ids["artifact"])
    artifact.sha256 = ""
    db_session.commit()
    result = _execute(db_session, run, _payload([f"artifact:{artifact.id}"]))
    assert result.status == "BLOCKED"


# ── 3. 跨项目 / resolver 异常 / 缺失 ──────────────────────
def test_cross_project_resolver_refuses(db_session):
    _project(db_session, 1)
    run = _run(db_session, project_id=2, key="RUN-EV-7")
    with pytest.raises(EvidenceResolverError):
        build_evidence_resolver(db_session, project_id=1, run_id=run.id)


def test_cross_project_artifact_blocks(db_session):
    run = _run(db_session, key="RUN-EV-8")
    other = _run(db_session, project_id=2, key="RUN-EV-P2")
    resolver = build_evidence_resolver(db_session, project_id=1, run_id=run.id)
    result = _execute(
        db_session,
        run,
        _payload([f"artifact:{other._evidence_ids['artifact']}"]),
        resolver=resolver,
    )
    assert result.status == "BLOCKED"


def test_resolver_unavailable_blocks(db_session):
    run = _run(db_session, key="RUN-EV-9")
    agent = _agent(_payload([f"artifact:{run._evidence_ids['artifact']}"]))
    adapter = BaseAgentAdapter(agent, key="A4")
    result = adapter.execute(
        AgentContext(project_id=1, run_id=run.id, evidence_resolver=None), "triage"
    )
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EVIDENCE"


def test_resolver_exception_blocks(db_session):
    run = _run(db_session, key="RUN-EV-10")

    def broken(_refs):
        raise RuntimeError("resolver down")

    result = _execute(
        db_session,
        run,
        _payload([f"artifact:{run._evidence_ids['artifact']}"]),
        resolver=broken,
    )
    assert result.status == "BLOCKED"


# ── 4. resolver 直接行为（存在/墓碑/跨项目）───────────────
def test_resolver_metadata_contract(db_session):
    run = _run(db_session, key="RUN-EV-11")
    resolver = build_evidence_resolver(db_session, project_id=1, run_id=run.id)
    entries = resolver(
        [
            f"assertion:{run._evidence_ids['assertion']}",
            f"attempt:{run._evidence_ids['attempt']}",
            f"artifact:{run._evidence_ids['artifact']}",
            f"run:{run.id}",
            "artifact:missing",
            "",
        ]
    )
    by_ref = {entry["ref"]: entry for entry in entries}
    assert by_ref[f"run:{run.id}"]["valid"] is True
    assert by_ref["artifact:missing"]["valid"] is False
    assert by_ref[""]["reason"] == "EMPTY_REF"
    assert by_ref["artifact:missing"]["reason"] == "NOT_FOUND"
    assert all("checksum" in entry for entry in entries if entry["valid"])


def test_a4_validate_requires_supporting_evidence(db_session):
    run = _run(db_session, key="RUN-EV-12")
    bad = _payload([])
    bad["hypotheses"][0]["supporting_evidence"] = []
    result = _execute(db_session, run, bad)
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EVIDENCE"
