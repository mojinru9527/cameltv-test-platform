"""VersionTask service — 版本验收任务唯一事实源 + 状态机 + 旧数据只读兼容映射（B6）。"""
from __future__ import annotations

import json
import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.release_bundle import ReleaseBundle
from app.models.version_mission import VersionMission
from app.models.version_task import VersionTask, VersionTaskDefect, VersionTaskExecution
from app.models.version_task_plan import VersionTaskPlanItem
from app.core.exceptions import APIException, not_found

logger = logging.getLogger("version_task")

# 状态机：从唯一主线「建任务 → 审方案 → 看执行 → 下结论」派生。
TRANSITIONS: dict[str, set[str]] = {
    "draft": {"plan_review", "cancelled"},
    "plan_review": {"approved", "blocked", "cancelled"},
    "approved": {"executing", "blocked", "cancelled"},
    "executing": {"executed", "blocked", "cancelled"},
    "executed": {"verdict", "blocked", "cancelled"},
    "verdict": {"released"},
    "released": set(),
    "blocked": {"draft"},
    "cancelled": set(),
}

VALID_VERDICTS = {"", "pass", "blocked", "conditional"}


def _to_int_dict(raw: str | None, default: dict | None = None) -> dict:
    if not raw:
        return dict(default or {})
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return dict(default or {})


def create_task(
    db: Session,
    *,
    project_id: int,
    title: str,
    version: str,
    source: str = "manual",
    source_mission_id: int | None = None,
    source_bundle_id: int | None = None,
    requirement_doc_id: int | None = None,
    release_bundle_id: int | None = None,
    environment_id: int | None = None,
    scope: dict | None = None,
    created_by: int = 0,
    qa_owner_id: int = 0,
) -> VersionTask:
    task = VersionTask(
        project_id=project_id,
        title=title,
        version=version,
        source=source,
        source_mission_id=source_mission_id,
        source_bundle_id=source_bundle_id,
        requirement_doc_id=requirement_doc_id,
        release_bundle_id=release_bundle_id,
        environment_id=environment_id,
        scope=json.dumps(scope or {}, ensure_ascii=False),
        created_by=created_by,
        qa_owner_id=qa_owner_id,
        status="draft",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    project_id: int,
    *,
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[VersionTask], int]:
    q = select(VersionTask).where(VersionTask.project_id == project_id)
    if status:
        q = q.where(VersionTask.status == status)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(VersionTask.title.ilike(like), VersionTask.version.ilike(like)))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.execute(q.order_by(VersionTask.id.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return list(rows), total


def get_task(db: Session, task_id: int) -> VersionTask:
    task = db.get(VersionTask, task_id)
    if task is None:
        raise not_found("版本验收任务不存在")
    return task


def update_task(db: Session, task_id: int, data: dict) -> VersionTask:
    task = get_task(db, task_id)
    for key, value in data.items():
        if value is not None:
            if key == "scope" and isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def transition_task(
    db: Session, task_id: int, to_status: str, verdict: str = "", summary: str | None = None
) -> VersionTask:
    task = get_task(db, task_id)
    allowed = TRANSITIONS.get(task.status, set())
    if to_status not in allowed:
        raise APIException(code=1, msg=f"非法状态流转：{task.status} -> {to_status}")
    if verdict and verdict not in VALID_VERDICTS:
        raise APIException(code=1, msg=f"非法结论：{verdict}")
    task.status = to_status
    if verdict:
        task.verdict = verdict
    if summary is not None:
        task.summary = summary
    if to_status == "released" and not task.verdict:
        task.verdict = "pass"
    db.commit()
    db.refresh(task)
    return task


def add_execution(
    db: Session, task_id: int, execution_type: str, execution_id: int, ref: str = ""
) -> VersionTaskExecution:
    task = get_task(db, task_id)
    link = VersionTaskExecution(
        task_id=task.id, execution_type=execution_type, execution_id=execution_id, ref=ref
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def add_defect(db: Session, task_id: int, defect_id: int) -> VersionTaskDefect:
    task = get_task(db, task_id)
    link = VersionTaskDefect(task_id=task.id, defect_id=defect_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def _mission_to_task_dict(mission: VersionMission, release: ReleaseBundle | None) -> dict:
    """旧数据（VersionMission）只读兼容映射到 VersionTask 视图。不写库、不双写。"""
    return {
        "id": f"mission:{mission.id}",
        "project_id": mission.project_id,
        "title": mission.title,
        "version": mission.version,
        "source": "mission",
        "source_mission_id": mission.id,
        "source_bundle_id": release.id if release else mission.test_plan_id,
        "requirement_doc_id": mission.requirement_doc_id,
        "release_bundle_id": release.id if release else None,
        "environment_id": mission.environment_id,
        "status": "draft",
        "verdict": "",
        "summary": mission.summary,
        "scope": _to_int_dict(mission.scope),
        "created_by": mission.created_by,
        "qa_owner_id": mission.qa_owner_id,
        "legacy": True,
    }


def compat_mission_view(db: Session, mission_id: int) -> dict:
    """VersionMission -> VersionTask 只读视图（兼容映射，绝无双写）。"""
    mission = db.get(VersionMission, mission_id)
    if mission is None:
        raise not_found("旧智能测试任务不存在")
    release = db.get(ReleaseBundle, mission.test_plan_id) if mission.test_plan_id else None
    return _mission_to_task_dict(mission, release)


def compat_mission_list(db: Session, project_id: int, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    q = select(VersionMission).where(VersionMission.project_id == project_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = (
        db.execute(q.order_by(VersionMission.id.desc()).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    items = []
    for r in rows:
        release = db.get(ReleaseBundle, r.test_plan_id) if r.test_plan_id else None
        items.append(_mission_to_task_dict(r, release))
    return items, total


PLAN_ACTIONS = {"adopt", "modify", "remove", "ask", "confirm"}


def get_plan(db: Session, task_id: int) -> list[VersionTaskPlanItem]:
    task = get_task(db, task_id)
    return sorted(task.plan_items, key=lambda x: (x.order_index, x.id))


def generate_plan(db: Session, task_id: int, items: list[dict]) -> list[VersionTaskPlanItem]:
    """把 AI 生成的验收方案条目写入 VersionTask（B7）。返回全部方案条目。"""
    task = get_task(db, task_id)
    start = max((i.order_index for i in task.plan_items), default=0)
    for idx, it in enumerate(items):
        item = VersionTaskPlanItem(
            task_id=task.id,
            item_type=it.get("item_type", "functional"),
            title=it.get("title", ""),
            description=it.get("description", ""),
            confidence=int(it.get("confidence", 0)),
            status="draft",
            question=it.get("question", ""),
            order_index=start + idx + 1,
        )
        db.add(item)
    db.commit()
    return get_plan(db, task_id)


def review_plan_item(db: Session, plan_item_id: int, action: str, patch: dict | None = None) -> VersionTaskPlanItem:
    """人工审核方案条目：采纳 / 修改 / 删除 / 追问 / 确认（B7 审核面板）。"""
    item = db.get(VersionTaskPlanItem, plan_item_id)
    if item is None:
        raise not_found("验收方案条目不存在")
    if action not in PLAN_ACTIONS:
        raise APIException(code=1, msg=f"非法审核动作：{action}")
    patch = patch or {}
    if action == "adopt":
        item.status = "adopted"
    elif action == "confirm":
        item.status = "adopted"
    elif action == "modify":
        item.status = "modified"
        item.title = patch.get("title", item.title)
        item.description = patch.get("description", item.description)
        if "confidence" in patch:
            item.confidence = int(patch.get("confidence", item.confidence))
    elif action == "remove":
        item.status = "removed"
    elif action == "ask":
        item.status = "asked"
        item.question = patch.get("question", item.question)
    if "answer" in patch:
        item.answer = patch.get("answer", item.answer)
    db.commit()
    db.refresh(item)
    return item
