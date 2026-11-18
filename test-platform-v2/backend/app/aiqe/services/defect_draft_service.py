"""AUD-012：可复现 Defect Draft（服务端证据校验 + Reproduction Bundle）。

v1.5 §02 AUD-012：

- 后端必须验证 evidence refs 真实存在、同 Project、同 Run（``evidence_service``）；
- 缺陷必须关联至少一个失败断言，或明确说明为什么没有断言；
- 生成脱敏的 ``ReproductionBundle``（Workflow Snapshot / Fixture Recipe / Environment
  Snapshot / Artifact refs / 复现命令），**不得打包真实 Secret**；
- 人工确认后才转正式缺陷，保留 draft 审计（``draft_id`` / ``approved_by``）。
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.profile import ExecutionProfile
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.redaction import assert_no_secret, redact_mapping
from app.aiqe.services.evidence_service import (
    resolve_evidence_refs,
)
from app.models.defect import Defect

FAILING_STATUSES = frozenset({"FAIL", "BLOCKED", "ERROR", "NOT_EVALUATED"})


class DefectDraftError(ValueError):
    pass


@dataclass(frozen=True)
class ReproductionBundle:
    defect_id: int
    title: str
    severity: str
    build_sha: str
    environment_snapshot: dict[str, Any] = field(default_factory=dict)
    workflow_snapshot: dict[str, Any] = field(default_factory=dict)
    fixture_recipe: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    assertions: list[dict[str, Any]] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = redact_mapping(
            {
                "defect_id": self.defect_id,
                "title": self.title,
                "severity": self.severity,
                "build_sha": self.build_sha,
                "correlation_id": self.correlation_id,
                "environment_snapshot": self.environment_snapshot,
                "workflow_snapshot": self.workflow_snapshot,
                "fixture_recipe": self.fixture_recipe,
                "evidence": self.evidence,
                "steps": self.steps,
                "assertions": self.assertions,
                "commands": self.commands,
            }
        )
        assert_no_secret(payload, where="reproduction_bundle")
        return payload

    def to_markdown(self) -> str:
        data = self.to_dict()
        lines = [
            f"# 复现包：{data['title']}",
            "",
            f"- 缺陷 ID：{data['defect_id']}",
            f"- 严重级别：{data['severity']}",
            f"- Build SHA：`{data['build_sha']}`",
            f"- Correlation：`{data['correlation_id'] or '-'}`",
            "",
            "## 环境快照",
            "```json",
            json.dumps(data["environment_snapshot"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Fixture Recipe",
            "```json",
            json.dumps(data["fixture_recipe"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## 复现步骤",
        ]
        for index, step in enumerate(data["steps"], start=1):
            lines.append(
                f"{index}. [{step.get('driver') or '-'}] "
                f"{step.get('action') or ''} → 期望：{step.get('expected') or '-'}"
            )
        lines.extend(["", "## 失败断言"])
        for assertion in data["assertions"]:
            lines.append(
                f"- `{assertion.get('ref')}` 状态={assertion.get('status')} "
                f"期望={assertion.get('expected')} 实际={assertion.get('actual')}"
            )
        lines.extend(["", "## 证据"])
        for item in data["evidence"]:
            lines.append(f"- `{item.get('ref')}`（{item.get('kind')}）")
        lines.extend(["", "## 复现命令", "```bash"])
        lines.extend(data["commands"] or ["# 无可用命令（需人工在测试环境执行）"])
        lines.extend(["```", ""])
        return "\n".join(lines)

    def to_zip(self) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "reproduction-bundle.json",
                json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            )
            archive.writestr("reproduction.md", self.to_markdown())
        return buffer.getvalue()


def _latest_attempt(db: Session, node: NodeRun) -> StepAttempt | None:
    return db.scalar(
        select(StepAttempt)
        .where(StepAttempt.node_run_id == node.id)
        .order_by(StepAttempt.attempt_no.desc())
    )


def failing_assertion_refs(
    db: Session, *, run_id: str, attempt_id: str | None = None
) -> list[str]:
    rows = db.execute(
        select(RunAssertionResult, StepAttempt)
        .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
        .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
        .where(NodeRun.run_id == run_id)
    ).all()
    refs: list[str] = []
    for assertion, attempt in rows:
        if attempt_id is not None and attempt.id != attempt_id:
            continue
        if assertion.status in FAILING_STATUSES:
            refs.append(f"assertion:{attempt.id}:{assertion.assertion_key}")
    return sorted(set(refs))


def build_defect_draft(
    db: Session,
    *,
    project_id: int,
    run_id: str,
    title: str,
    severity: str = "P2",
    description: str = "",
    evidence_refs: list[str] | None = None,
    ac_refs: list[str] | None = None,
    node_run_id: str | None = None,
    attempt_id: str | None = None,
    failing_assertion_refs_override: list[str] | None = None,
    no_assertion_reason: str = "",
    creator_id: int = 0,
    correlation_id: str = "",
) -> Defect:
    run = db.get(TestRun, run_id)
    if run is None or int(run.project_id or 0) != int(project_id):
        raise DefectDraftError(f"run 不存在或不属于当前 Project: {run_id}")
    if node_run_id is not None:
        node = db.get(NodeRun, node_run_id)
        if node is None or node.run_id != run.id:
            raise DefectDraftError("node_run 不属于该 Run")

    refs = list(evidence_refs or [])
    resolved = resolve_evidence_refs(db, project_id=project_id, run_id=run.id, refs=refs)

    assertion_refs = list(failing_assertion_refs_override or [])
    if not assertion_refs:
        assertion_refs = failing_assertion_refs(db, run_id=run.id, attempt_id=attempt_id)
    if not assertion_refs and not str(no_assertion_reason or "").strip():
        raise DefectDraftError(
            "缺陷草稿必须关联至少一个失败断言，或提供 no_assertion_reason（例如 Runner 崩溃）"
        )
    if assertion_refs:
        resolve_evidence_refs(
            db, project_id=project_id, run_id=run.id, refs=assertion_refs
        )

    title_text = str(title or "").strip()
    if not title_text:
        raise DefectDraftError("title 不能为空")
    existing = db.scalar(
        select(Defect).where(
            Defect.project_id == int(project_id),
            Defect.aiqe_run_id == run.id,
            Defect.title == title_text,
            Defect.is_draft.is_(True),
        )
    )
    if existing is not None:
        return existing

    safe_description = redact_mapping(description)[:4000] if description else ""
    draft = Defect(
        project_id=int(project_id),
        title=title_text[:300],
        description=safe_description,
        severity=str(severity or "P2")[:10],
        status="open",
        is_draft=True,
        aiqe_run_id=run.id,
        aiqe_node_run_id=node_run_id,
        evidence_refs_json=[item["ref"] for item in (x.payload() for x in resolved)],
        failing_assertion_refs_json=assertion_refs,
        ac_refs_json=list(ac_refs or []),
        no_assertion_reason=str(no_assertion_reason or "")[:1000],
        correlation_id=str(correlation_id or "")[:128],
        fixture_namespace=str(
            (run.environment_snapshot_json or {}).get("fixture_namespace", "")
        )[:128],
        reproduction_status="COMPLETE" if assertion_refs else "REPRODUCTION_INCOMPLETE",
        creator_id=int(creator_id or 0),
    )
    db.add(draft)
    db.flush()
    draft.draft_id = str(draft.id)
    db.flush()
    return draft


def build_bundle(db: Session, *, project_id: int, defect: Defect) -> ReproductionBundle:
    if int(defect.project_id or 0) != int(project_id):
        raise DefectDraftError("缺陷不属于当前 Project")
    run = db.get(TestRun, defect.aiqe_run_id) if defect.aiqe_run_id else None
    if run is None:
        raise DefectDraftError("缺陷缺少关联 Run，无法生成复现包")
    workflow_snapshot: dict[str, Any] = {}
    if run.workflow_definition_id:
        definition = db.get(WorkflowDefinition, run.workflow_definition_id)
        if definition is not None:
            workflow_snapshot = {
                "workflow_id": definition.id,
                "version": definition.version,
                "checksum": definition.checksum,
                "graph": definition.graph_json,
            }
    profile_snapshot: dict[str, Any] = {}
    if run.execution_profile_id:
        profile = db.get(ExecutionProfile, run.execution_profile_id)
        if profile is not None:
            profile_snapshot = {
                "profile_id": profile.id,
                "purpose": profile.purpose,
                "checksum": profile.checksum,
                "config": profile.config_json,
            }
    evidence = []
    if defect.evidence_refs_json:
        resolved = resolve_evidence_refs(
            db,
            project_id=project_id,
            run_id=run.id,
            refs=list(defect.evidence_refs_json),
        )
        evidence = [item.payload() for item in resolved]
    assertion_details: list[dict[str, Any]] = []
    for ref in defect.failing_assertion_refs_json or []:
        kind, _, identifier = str(ref).partition(":")
        if kind != "assertion":
            continue
        attempt_id, _, key = identifier.partition(":")
        row = db.scalar(
            select(RunAssertionResult).where(
                RunAssertionResult.step_attempt_id == attempt_id,
                RunAssertionResult.assertion_key == key,
            )
        )
        if row is None:
            continue
        assertion_details.append(
            {
                "ref": ref,
                "status": row.status,
                "expected": row.expected_json,
                "actual": row.actual_json,
                "oracle_id": row.oracle_id,
                "source_ref": row.source_ref,
            }
        )
    nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    steps = [
        {
            "node_key": node.node_key,
            "driver": node.driver_key,
            "action": (node.input_ref or {}).get("action")
            or (node.input_ref or {}).get("url")
            or "",
            "expected": (node.input_ref or {}).get("expected_status", ""),
            "status": node.status,
        }
        for node in nodes
    ]
    commands = [
        f"# 在隔离测试环境执行（Run {run.run_key}）",
        f"python -m pytest tests/e2e/aiqe -q  # 使用 defect #{defect.id} 关联 Run {run.id}",
    ]
    bundle = ReproductionBundle(
        defect_id=int(defect.id),
        title=defect.title,
        severity=defect.severity,
        build_sha=run.commit_sha or run.build_ref or "",
        environment_snapshot={
            "run_id": run.id,
            "environment_id": run.environment_id,
            "profile": profile_snapshot,
            "environment_snapshot": redact_mapping(run.environment_snapshot_json or {}),
        },
        workflow_snapshot=workflow_snapshot,
        fixture_recipe={
            "fixture_namespace": defect.fixture_namespace
            or (run.environment_snapshot_json or {}).get("fixture_namespace", ""),
            "cleanup_policy": "run_scoped_only",
        },
        evidence=evidence,
        steps=steps,
        assertions=assertion_details,
        commands=commands,
        correlation_id=defect.correlation_id,
    )
    bundle.to_dict()  # 触发脱敏断言
    return bundle


def promote_draft(
    db: Session, *, defect_id: int, project_id: int, approver_id: int
) -> Defect:
    defect = db.get(Defect, defect_id)
    if defect is None or int(defect.project_id or 0) != int(project_id):
        raise DefectDraftError(f"缺陷不存在: {defect_id}")
    if not defect.is_draft:
        raise DefectDraftError("该缺陷不是草稿，无需确认")
    defect.is_draft = False
    defect.draft_id = defect.draft_id or str(defect.id)
    defect.approved_by = int(approver_id)
    defect.approved_at = datetime.now(UTC)
    db.flush()
    return defect


__all__ = [
    "DefectDraftError",
    "ReproductionBundle",
    "build_bundle",
    "build_defect_draft",
    "failing_assertion_refs",
    "promote_draft",
]
