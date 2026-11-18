"""AUD-016 / AUD-012：Evidence Ref 服务端解析（存在性 + 项目/Run scope）。

v1.5 §03 AUD-016 第 1 条、§02 AUD-012「后端校验 evidence refs」：

- Agent / Defect Draft 给出的每个引用都必须由服务端解析：**存在、归属同 Project、
  属于相关 Run**；任一不满足则整个结果验证失败；
- 只做前缀字符串校验（旧实现）等于没有校验，必须替换；
- 解析失败返回 ``EVIDENCE_REF_INVALID``，不允许静默丢弃。

支持的前缀：``artifact:`` / ``event:`` / ``run:`` / ``node:`` / ``attempt:`` /
``assertion:<attempt_id>:<key>`` / ``signal:<key>``（signal 为 Detector 观测，允许只校验格式）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.event import RunEvent
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun

SUPPORTED_PREFIXES: frozenset[str] = frozenset(
    {"artifact", "event", "run", "node", "attempt", "assertion", "signal"}
)


class EvidenceRefError(ValueError):
    def __init__(self, ref: str, reason: str) -> None:
        super().__init__(f"EVIDENCE_REF_INVALID: {ref!r} ({reason})")
        self.code = "EVIDENCE_REF_INVALID"
        self.ref = ref
        self.reason = reason


@dataclass(frozen=True)
class ResolvedEvidenceRef:
    ref: str
    kind: str
    identifier: str
    project_id: int
    run_id: str | None
    metadata: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "kind": self.kind,
            "id": self.identifier,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "metadata": self.metadata,
        }


def parse_ref(ref: str) -> tuple[str, str]:
    text = str(ref or "").strip()
    if ":" not in text:
        raise EvidenceRefError(text, "引用缺少类型前缀")
    kind, _, identifier = text.partition(":")
    if kind not in SUPPORTED_PREFIXES:
        raise EvidenceRefError(text, f"不支持的前缀: {kind}")
    if not identifier.strip():
        raise EvidenceRefError(text, "引用缺少标识")
    return kind, identifier.strip()


def _resolve_one(
    db: Session,
    *,
    ref: str,
    kind: str,
    identifier: str,
    project_id: int,
    run_id: str | None,
) -> ResolvedEvidenceRef:
    if kind == "artifact":
        artifact_row = db.get(RunArtifact, identifier)
        if artifact_row is None:
            raise EvidenceRefError(ref, "artifact 不存在")
        owner = db.get(TestRun, artifact_row.run_id)
        if owner is None or int(owner.project_id or 0) != int(project_id):
            raise EvidenceRefError(ref, "artifact 不属于当前 Project")
        if run_id is not None and artifact_row.run_id != run_id:
            raise EvidenceRefError(ref, "artifact 不属于相关 Run")
        return ResolvedEvidenceRef(
            ref=ref,
            kind=kind,
            identifier=identifier,
            project_id=int(project_id),
            run_id=artifact_row.run_id,
            metadata={
                "artifact_type": artifact_row.artifact_type,
                "upload_status": artifact_row.upload_status,
                "sha256": artifact_row.sha256,
                "size_bytes": artifact_row.size_bytes,
                "node_run_id": artifact_row.node_run_id,
            },
        )
    if kind == "event":
        event_row = db.get(RunEvent, identifier)
        if event_row is None:
            raise EvidenceRefError(ref, "event 不存在")
        owner = db.get(TestRun, event_row.run_id)
        if owner is None or int(owner.project_id or 0) != int(project_id):
            raise EvidenceRefError(ref, "event 不属于当前 Project")
        if run_id is not None and event_row.run_id != run_id:
            raise EvidenceRefError(ref, "event 不属于相关 Run")
        return ResolvedEvidenceRef(
            ref=ref,
            kind=kind,
            identifier=identifier,
            project_id=int(project_id),
            run_id=event_row.run_id,
            metadata={"event_type": event_row.event_type, "seq": event_row.seq},
        )
    if kind == "run":
        run_row = db.get(TestRun, identifier)
        if run_row is None or int(run_row.project_id or 0) != int(project_id):
            raise EvidenceRefError(ref, "run 不存在或不属于当前 Project")
        if run_id is not None and run_row.id != run_id:
            raise EvidenceRefError(ref, "run 不属于相关 Run")
        return ResolvedEvidenceRef(
            ref=ref,
            kind=kind,
            identifier=identifier,
            project_id=int(project_id),
            run_id=run_row.id,
            metadata={"status": run_row.status, "outcome": run_row.outcome},
        )
    if kind == "node":
        node_row = db.get(NodeRun, identifier)
        if node_row is None:
            raise EvidenceRefError(ref, "node 不存在")
        owner = db.get(TestRun, node_row.run_id)
        if owner is None or int(owner.project_id or 0) != int(project_id):
            raise EvidenceRefError(ref, "node 不属于当前 Project")
        if run_id is not None and node_row.run_id != run_id:
            raise EvidenceRefError(ref, "node 不属于相关 Run")
        return ResolvedEvidenceRef(
            ref=ref,
            kind=kind,
            identifier=identifier,
            project_id=int(project_id),
            run_id=node_row.run_id,
            metadata={"node_key": node_row.node_key, "status": node_row.status},
        )
    if kind == "attempt":
        attempt_row = db.get(StepAttempt, identifier)
        if attempt_row is None:
            raise EvidenceRefError(ref, "attempt 不存在")
        node = db.get(NodeRun, attempt_row.node_run_id)
        owner = db.get(TestRun, node.run_id) if node is not None else None
        if owner is None or int(owner.project_id or 0) != int(project_id):
            raise EvidenceRefError(ref, "attempt 不属于当前 Project")
        if run_id is not None and owner.id != run_id:
            raise EvidenceRefError(ref, "attempt 不属于相关 Run")
        return ResolvedEvidenceRef(
            ref=ref,
            kind=kind,
            identifier=identifier,
            project_id=int(project_id),
            run_id=owner.id,
            metadata={"status": attempt_row.status, "attempt_no": attempt_row.attempt_no},
        )
    if kind == "assertion":
        attempt_id, _, key = identifier.partition(":")
        if not attempt_id or not key:
            raise EvidenceRefError(ref, "assertion 引用格式应为 assertion:<attempt_id>:<key>")
        assertion_row = db.scalar(
            select(RunAssertionResult).where(
                RunAssertionResult.step_attempt_id == attempt_id,
                RunAssertionResult.assertion_key == key,
            )
        )
        if assertion_row is None:
            raise EvidenceRefError(ref, "assertion 不存在")
        attempt = db.get(StepAttempt, attempt_id)
        node = db.get(NodeRun, attempt.node_run_id) if attempt is not None else None
        owner = db.get(TestRun, node.run_id) if node is not None else None
        if owner is None or int(owner.project_id or 0) != int(project_id):
            raise EvidenceRefError(ref, "assertion 不属于当前 Project")
        if run_id is not None and owner.id != run_id:
            raise EvidenceRefError(ref, "assertion 不属于相关 Run")
        return ResolvedEvidenceRef(
            ref=ref,
            kind=kind,
            identifier=identifier,
            project_id=int(project_id),
            run_id=owner.id,
            metadata={
                "status": assertion_row.status,
                "required": bool(assertion_row.required),
                "source_ref": assertion_row.source_ref,
            },
        )
    # signal：Detector 观测，允许只校验格式（不落库）
    return ResolvedEvidenceRef(
        ref=ref,
        kind=kind,
        identifier=identifier,
        project_id=int(project_id),
        run_id=run_id,
        metadata={"format_only": True},
    )


def resolve_evidence_refs(
    db: Session,
    *,
    project_id: int,
    run_id: str | None,
    refs: list[str] | tuple[str, ...],
) -> list[ResolvedEvidenceRef]:
    """全部解析成功才返回；任一失败抛 ``EvidenceRefError``（整个结果验证失败）。"""
    if not refs:
        return []
    resolved: list[ResolvedEvidenceRef] = []
    seen: set[str] = set()
    for raw in refs:
        ref = str(raw or "").strip()
        if not ref or ref in seen:
            continue
        seen.add(ref)
        kind, identifier = parse_ref(ref)
        resolved.append(
            _resolve_one(
                db,
                ref=ref,
                kind=kind,
                identifier=identifier,
                project_id=int(project_id),
                run_id=run_id,
            )
        )
    return resolved


def assert_valid_evidence_refs(
    db: Session,
    *,
    project_id: int,
    run_id: str | None,
    refs: list[str] | tuple[str, ...],
) -> None:
    resolve_evidence_refs(db, project_id=project_id, run_id=run_id, refs=refs)


__all__ = [
    "SUPPORTED_PREFIXES",
    "EvidenceRefError",
    "ResolvedEvidenceRef",
    "assert_valid_evidence_refs",
    "parse_ref",
    "resolve_evidence_refs",
]
