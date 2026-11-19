"""V16-012：服务端 Evidence Resolver（A4 归因证据唯一可信入口）。

职责：
- 批量解析 ``artifact:<id>`` / ``assertion:<id>`` / ``attempt:<id>`` / ``step:<id>`` /
  ``event:<id>`` / ``run:<id>``；
- 校验资源存在、未删除/未墓碑、属于当前 Project、属于当前 Run（或授权 source Run）、
  类型允许、checksum 可验证；
- 只返回 canonical metadata（不含 Secret 原文），敏感字段已由 Artifact/Assertion
  管道脱敏；解析失败/异常由调用方 fail-closed。
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.event import RunEvent
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun

ALLOWED_RUN_ROLES = {"current", "retest_of", "source"}


class EvidenceResolverError(RuntimeError):
    pass


def _artifact(db: Session, ref: str, *, project_id: int, run: TestRun) -> dict[str, Any]:
    row = db.get(RunArtifact, ref)
    if row is None:
        return _invalid(ref, "NOT_FOUND", kind="artifact")
    if row.deleted_at is not None:
        return _invalid(ref, "EVIDENCE_TOMBSTONED", kind="artifact", tombstoned=True)
    if row.project_id is not None and int(row.project_id) != int(project_id):
        return _invalid(ref, "CROSS_PROJECT", kind="artifact")
    if str(row.run_id) != str(run.id):
        return _invalid(ref, "CROSS_RUN", kind="artifact")
    if not str(row.sha256 or ""):
        return _invalid(ref, "CHECKSUM_MISSING", kind="artifact")
    return {
        "ref": ref,
        "valid": True,
        "kind": "artifact",
        "project_id": int(project_id),
        "run_id": str(row.run_id),
        "checksum": str(row.sha256),
        "tombstoned": False,
    }


def _assertion(db: Session, ref: str, *, project_id: int, run: TestRun) -> dict[str, Any]:
    row = db.get(RunAssertionResult, ref)
    if row is None:
        return _invalid(ref, "NOT_FOUND", kind="assertion")
    attempt = db.get(StepAttempt, row.step_attempt_id)
    node = db.get(NodeRun, attempt.node_run_id) if attempt is not None else None
    if node is None:
        return _invalid(ref, "NODE_MISSING", kind="assertion")
    if str(node.run_id) != str(run.id):
        return _invalid(ref, "CROSS_RUN", kind="assertion")
    if int(run.project_id or 0) != int(project_id):
        return _invalid(ref, "CROSS_PROJECT", kind="assertion")
    return {
        "ref": ref,
        "valid": True,
        "kind": "assertion",
        "project_id": int(project_id),
        "run_id": str(run.id),
        "checksum": str(getattr(attempt, "output_hash", "") or ""),
        "tombstoned": False,
    }


def _attempt(db: Session, ref: str, *, project_id: int, run: TestRun) -> dict[str, Any]:
    row = db.get(StepAttempt, ref)
    if row is None:
        return _invalid(ref, "NOT_FOUND", kind="attempt")
    node = db.get(NodeRun, row.node_run_id)
    if node is None:
        return _invalid(ref, "NODE_MISSING", kind="attempt")
    if str(node.run_id) != str(run.id):
        return _invalid(ref, "CROSS_RUN", kind="attempt")
    return {
        "ref": ref,
        "valid": True,
        "kind": "attempt",
        "project_id": int(project_id),
        "run_id": str(run.id),
        "checksum": "",
        "tombstoned": False,
    }


def _event(db: Session, ref: str, *, project_id: int, run: TestRun) -> dict[str, Any]:
    row = db.get(RunEvent, ref)
    if row is None:
        return _invalid(ref, "NOT_FOUND", kind="event")
    if str(row.run_id) != str(run.id):
        return _invalid(ref, "CROSS_RUN", kind="event")
    return {
        "ref": ref,
        "valid": True,
        "kind": "event",
        "project_id": int(project_id),
        "run_id": str(run.id),
        "checksum": str(row.producer_event_id or ""),
        "tombstoned": False,
    }


def _run(db: Session, ref: str, *, project_id: int, run: TestRun) -> dict[str, Any]:
    row = db.get(TestRun, ref)
    if row is None:
        return _invalid(ref, "NOT_FOUND", kind="run")
    if int(row.project_id or 0) != int(project_id):
        return _invalid(ref, "CROSS_PROJECT", kind="run")
    authorized = {
        str(run.id),
        str(run.retest_of) if run.retest_of else "",
    }
    if str(row.id) not in authorized:
        return _invalid(ref, "CROSS_RUN", kind="run")
    return {
        "ref": ref,
        "valid": True,
        "kind": "run",
        "project_id": int(project_id),
        "run_id": str(row.id),
        "checksum": str(row.workflow_checksum or ""),
        "tombstoned": False,
    }


def _invalid(ref: str, reason: str, *, kind: str = "", tombstoned: bool = False) -> dict[str, Any]:
    return {
        "ref": ref,
        "valid": False,
        "reason": reason,
        "kind": kind,
        "tombstoned": bool(tombstoned),
    }


_RESOLVERS = {
    "artifact": _artifact,
    "assertion": _assertion,
    "attempt": _attempt,
    "step": _attempt,
    "event": _event,
    "run": _run,
}


def build_evidence_resolver(
    db: Session, *, project_id: int, run_id: str
) -> Any:
    """构造绑定 Project/Run 的 resolver；调用方 fail-closed。"""
    run = db.get(TestRun, str(run_id))
    if run is None or int(run.project_id or 0) != int(project_id):
        raise EvidenceResolverError(f"Run 不存在或不属于当前项目: {run_id}")

    def resolve(refs: Iterable[str]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for raw in refs:
            ref = str(raw or "").strip()
            if not ref:
                output.append(_invalid("", "EMPTY_REF"))
                continue
            kind, _, identifier = ref.partition(":")
            resolver = _RESOLVERS.get(kind)
            if resolver is None or not identifier:
                output.append(_invalid(ref, "UNKNOWN_REF_TYPE", kind=kind))
                continue
            entry = resolver(db, identifier, project_id=int(project_id), run=run)
            entry["ref"] = ref
            output.append(entry)
        return output

    return resolve


__all__ = [
    "ALLOWED_RUN_ROLES",
    "EvidenceResolverError",
    "build_evidence_resolver",
]
