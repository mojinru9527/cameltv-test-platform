"""Create defects that remain anchored to one AITDE execution attempt."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.defect import Defect
from app.modules.aitde.execution import repository


_FAILURE_OUTCOMES = {
    "BUSINESS_FAIL",
    "AUTOMATION_FAIL",
    "DATA_FAIL",
    "ENV_FAIL",
    "ASSERTION_ERROR",
    "BLOCKED",
    "INCONCLUSIVE",
}


def create_for_run(
    db: Session,
    run_id: int,
    *,
    project_id: int,
    user_id: int,
    severity: str = "P2",
    note: str = "",
) -> Defect:
    run = repository.get_run(db, run_id, project_id)
    if run is None:
        raise APIException(code=404, msg="执行记录不存在", http_status=404)
    if run.outcome not in _FAILURE_OUTCOMES:
        raise APIException(code=409, msg="该执行没有失败结果，不能创建缺陷", http_status=409)

    existing = db.scalar(
        select(Defect)
        .where(
            Defect.project_id == project_id,
            Defect.aitde_run_id == run.id,
            Defect.status.notin_(("closed", "rejected")),
        )
        .order_by(Defect.id.desc())
        .limit(1)
    )
    if existing is not None:
        return existing

    from app.services.defect_service import _generate_defect_id

    description = (
        f"来源：AI 全链路执行 Run #{run.id} / Scenario #{run.scenario_id}\n"
        f"结果：{run.outcome} / 证据状态：{run.evidence_status}"
    )
    if note.strip():
        description += f"\n补充：{note.strip()}"
    defect = Defect(
        project_id=project_id,
        defect_id=_generate_defect_id(db, project_id),
        title=f"执行失败：Scenario #{run.scenario_id}",
        description=description,
        severity=severity,
        status="open",
        aitde_run_id=run.id,
        creator_id=user_id,
    )
    db.add(defect)
    db.commit()
    db.refresh(defect)
    return defect
