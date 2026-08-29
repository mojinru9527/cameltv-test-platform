"""AITDE V3.3 ManualExecutionService (V33-008).

Tester-driven manual assist: a durable session + step state that survives a
refresh (DB-backed), with tester notes + evidence refs per step.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.manual.models import ManualExecutionSession, ManualExecutionStep
from app.modules.aitde.common.enums import ManualStepStatus


def create_session(
    db: Session,
    run_id: int,
    scenario_version_id: int,
    tester_id: int,
    browser_session_id: int | None = None,
) -> ManualExecutionSession:
    session = ManualExecutionSession(
        run_id=run_id, scenario_version_id=scenario_version_id,
        browser_session_id=browser_session_id, tester_id=tester_id, status="ACTIVE",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> ManualExecutionSession:
    s = db.get(ManualExecutionSession, session_id)
    if not s:
        raise APIException(code=404, msg="人工执行会话不存在", http_status=404)
    return s


def finish_session(db: Session, session_id: int) -> ManualExecutionSession:
    s = get_session(db, session_id)
    s.status = "FINISHED"
    s.finished_at = datetime.now()
    db.commit()
    db.refresh(s)
    return s


def add_step(db: Session, session_id: int, step_key: str) -> ManualExecutionStep:
    get_session(db, session_id)
    max_seq = db.scalar(
        select(ManualExecutionStep.sequence)
        .where(ManualExecutionStep.manual_session_id == session_id)
        .order_by(ManualExecutionStep.sequence.desc())
    )
    sequence = (max_seq or 0) + 1
    step = ManualExecutionStep(
        manual_session_id=session_id, sequence=sequence, step_key=step_key,
        status=ManualStepStatus.PENDING.value,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def complete_step(
    db: Session,
    step_id: int,
    status: str,
    tester_note: str = "",
    evidence_refs: list[int] | None = None,
) -> ManualExecutionStep:
    step = db.get(ManualExecutionStep, step_id)
    if not step:
        raise APIException(code=404, msg="人工步骤不存在", http_status=404)
    if status not in {s.value for s in ManualStepStatus}:
        raise APIException(code=400, msg=f"非法步骤状态：{status}", http_status=400)
    step.status = status
    step.tester_note = tester_note
    step.evidence_refs_json = json.dumps(evidence_refs or [], ensure_ascii=False)
    step.completed_at = datetime.now() if status != ManualStepStatus.PENDING.value else None
    db.commit()
    db.refresh(step)
    return step


def list_steps(db: Session, session_id: int) -> list[ManualExecutionStep]:
    get_session(db, session_id)
    rows = db.scalars(
        select(ManualExecutionStep)
        .where(ManualExecutionStep.manual_session_id == session_id)
        .order_by(ManualExecutionStep.sequence.asc())
    ).all()
    return list(rows)
