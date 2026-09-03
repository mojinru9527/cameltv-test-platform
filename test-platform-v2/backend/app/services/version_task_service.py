"""VersionTask service — 版本验收任务唯一事实源 + 状态机 + 旧数据只读兼容映射（B6）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.release_bundle import ReleaseBundle
from app.models.version_mission import VersionMission
from app.models.version_task import VersionTask, VersionTaskDefect, VersionTaskExecution
from app.models.version_task_plan import VersionTaskPlanItem
from app.models.version_task_run import VersionTaskRun
from app.models.defect import Defect
from app.models.notification import NotificationLog
from app.models.requirement import RequirementDocument
from app.models.version_knowledge import VersionKnowledgeRecord
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
            exec_meta=json.dumps(it.get("exec_meta") or {}, ensure_ascii=False),
        )
        db.add(item)
    db.commit()
    return get_plan(db, task_id)


def ai_generate_plan(db: Session, task_id: int, project_id: int) -> list[VersionTaskPlanItem]:
    """F-01：由项目级 AI 方案生成服务产出**可执行**验收方案条目并写入。"""
    from app.services import version_task_ai_service

    task = get_task(db, task_id)
    ctx = _task_ai_context(db, task)
    items = version_task_ai_service.generate_plan_items(db, ctx, project_id)
    return generate_plan(db, task_id, items)


def _task_ai_context(db: Session, task: VersionTask) -> dict:
    """组装 AI 方案生成所需的任务上下文（标题/版本/模块 + 可选需求文档正文）。"""
    context = ""
    if task.requirement_doc_id:
        try:
            doc = db.get(RequirementDocument, task.requirement_doc_id)
            if doc and getattr(doc, "content", ""):
                context = str(getattr(doc, "content", ""))[:6000]
        except Exception:  # noqa: BLE001 - 需求正文缺失不影响方案生成
            context = ""
    return {
        "title": task.title,
        "version": task.version,
        "scope": _to_int_dict(task.scope),
        "context": context,
    }


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



FAILURE_KINDS = {"business", "script", "data", "environment"}
FAILURE_KIND_LABEL = {
    "business": "业务缺陷",
    "script": "脚本缺陷",
    "data": "数据缺陷",
    "environment": "环境缺陷",
}


def _now():
    return datetime.now(timezone.utc)


def list_runs(db: Session, task_id: int) -> list[VersionTaskRun]:
    get_task(db, task_id)
    return list(db.query(VersionTaskRun).filter(VersionTaskRun.task_id == task_id).order_by(VersionTaskRun.id.desc()))


def get_run(db: Session, run_id: int) -> VersionTaskRun:
    run = db.get(VersionTaskRun, run_id)
    if run is None:
        raise not_found("执行运行记录不存在")
    return run


def start_run(db: Session, task_id: int) -> VersionTaskRun:
    """B8 一键运行：把版本任务的已采纳方案条目跑一遍，回写进度/覆盖/证据/失败四分类。"""
    task = get_task(db, task_id)

    # 状态机推进：draft/plan_review/approved 均可进入执行
    if task.status in ("draft", "plan_review", "approved", "executing"):
        task.status = "executing"
    else:
        raise APIException(code=1, msg=f"当前状态 {task.status} 不可执行")

    run = VersionTaskRun(task_id=task.id, status="running", progress=0, started_at=_now())
    db.add(run)
    db.commit()
    db.refresh(run)

    plan = get_plan(db, task_id)
    adopted_items = [i for i in plan if i.status in ("adopted", "modified")]
    total = max(len(adopted_items), 1)

    from app.services import version_task_exec_service

    base_url = version_task_exec_service.resolve_base_url(db, task)

    evidence = []
    failures = []
    passed = 0
    failed = 0
    skipped = 0
    blocked = 0
    now = _now().isoformat()
    for idx, item in enumerate(adopted_items):
        result = version_task_exec_service.execute_item(db, item, base_url)
        status = result["status"]
        if status == "pass":
            passed += 1
        elif status == "fail":
            failed += 1
            failure = result.get("failure") or {}
            failures.append({
                "item_id": item.id, "title": item.title,
                "kind": failure.get("kind", "business"),
                "evidence": f"/evidence/{run.id}/{item.id}",
                "message": failure.get("message", f"{item.title} 未通过"),
                "http_status": result.get("http_status"),
            })
        else:
            # not_run：无可执行目标，绝不臆造 PASS/FAIL —— 记 阻塞/未执行
            skipped += 1
            failures.append({
                "item_id": item.id, "title": item.title, "kind": "environment",
                "evidence": "",
                "message": f"{item.title} 未执行：{result.get('reason', '无可执行目标')}",
                "http_status": None,
            })
        for ev in result.get("evidence") or []:
            ev = dict(ev)
            ev["ts"] = now
            ev["ref"] = f"run:{run.id}:item:{item.id}"
            evidence.append(ev)

    if failed > 0:
        run_status = "failed"
    elif passed > 0 or skipped == 0:
        run_status = "done"
    else:
        run_status = "blocked"

    run.passed = passed
    run.failed = failed
    run.skipped = skipped
    run.blocked = blocked
    run.progress = 100
    run.status = run_status
    run.finished_at = _now()
    run.evidence = json.dumps(evidence, ensure_ascii=False)
    run.failures = json.dumps(failures, ensure_ascii=False)
    run.total = total
    db.commit()
    db.refresh(run)

    # 回写 coverage 到 VersionTask（C217-1），并转入 executed
    task = get_task(db, task_id)
    task.coverage = json.dumps(
        {"pass": run.passed, "fail": run.failed, "skip": run.skipped, "blocked": run.blocked},
        ensure_ascii=False,
    )
    task.status = "executed"
    db.commit()
    db.refresh(task)
    return run


def create_defect_draft(db: Session, run_id: int, failure_index: int, creator_id: int = 0) -> Defect:
    """把运行失败条目转成缺陷草稿（B8 失败自动分类→缺陷草稿）。"""
    run = get_run(db, run_id)
    failures = json.loads(run.failures or "[]")
    if failure_index < 0 or failure_index >= len(failures):
        raise APIException(code=1, msg="失败条目索引越界")
    f = failures[failure_index]
    kind = f.get("kind", "business")
    if kind not in FAILURE_KINDS:
        raise APIException(code=1, msg=f"未知失败类型：{kind}")
    defect = Defect(
        project_id=run.task_id,
        title=f"{FAILURE_KIND_LABEL[kind]}：{f.get('title', '')}",
        description=(
            f"来源：版本任务执行 {run.id} / 条目 {f.get('item_id')} \n"
            f"证据：{f.get('evidence')} \n消息：{f.get('message')}"
        ),
        severity="P2",
        status="open",
        creator_id=creator_id,
    )
    db.add(defect)
    db.commit()
    db.refresh(defect)
    link = VersionTaskDefect(task_id=run.task_id, defect_id=defect.id)
    db.add(link)
    db.commit()
    return defect


RELEASE_VERDICTS = {"pass", "blocked", "conditional"}


def build_release_package(db: Session, task_id: int) -> dict:
    """基于 VersionTask 的覆盖/结论/风险/缺陷生成可分享的放行证据包（B9）。"""
    task = get_task(db, task_id)
    coverage = json.loads(task.coverage or "{}")
    total = sum(int(coverage.get(k, 0)) for k in ("pass", "fail", "skip", "blocked")) or 1
    passed = int(coverage.get("pass", 0))
    pass_rate = round(passed * 100 / total, 1)
    risk = json.loads(task.risk or "[]")
    defects = [{"id": d.id, "defect_id": d.defect_id} for d in task.defects]
    return {
        "task_id": task.id,
        "title": task.title,
        "version": task.version,
        "status": task.status,
        "verdict": task.verdict,
        "coverage": coverage,
        "pass_rate": pass_rate,
        "total_checks": total,
        "risk": risk if isinstance(risk, list) else [risk],
        "defects": defects,
        "release_bundle_id": task.release_bundle_id,
        "summary": task.summary,
    }


def release_task(
    db: Session,
    task_id: int,
    verdict: str,
    release_bundle_id: int | None = None,
    risk: list | None = None,
    summary: str | None = None,
) -> dict:
    """B9 放行：设置 verdict/绑定发布包/生成放行证据包，状态机 verdict→released。"""
    task = get_task(db, task_id)
    if verdict not in RELEASE_VERDICTS:
        raise APIException(code=1, msg=f"非法放行结论：{verdict}")
    if task.status not in ("executed", "verdict"):
        raise APIException(code=1, msg=f"当前状态 {task.status} 不可放行")
    task.verdict = verdict
    if release_bundle_id is not None:
        task.release_bundle_id = release_bundle_id
    if risk is not None:
        task.risk = json.dumps(risk, ensure_ascii=False)
    if summary is not None:
        task.summary = summary
    task.status = "released"
    db.commit()
    db.refresh(task)
    record_version_knowledge(db, task_id)
    return build_release_package(db, task_id)


def notify_release(db: Session, task_id: int, message: str) -> None:
    """B9 通知：放行/打回后写一条系统通知。"""
    task = get_task(db, task_id)
    log = NotificationLog(
        project_id=task.project_id,
        event="version_release",
        status="sent",
        error=message or f"{task.title} 已放行：{task.verdict}",
    )
    db.add(log)
    db.commit()


def record_version_knowledge(db: Session, task_id: int) -> VersionKnowledgeRecord:
    """B11 版本沉淀：放行后记录「这版怎么测的」（需求→方案→结果→缺陷→放行结论）。"""
    task = get_task(db, task_id)
    existing = db.query(VersionKnowledgeRecord).filter_by(task_id=task.id).first()
    if existing:
        return existing
    coverage = json.loads(task.coverage or "{}")
    risk = json.loads(task.risk or "[]")
    plan = [{"item_type": i.item_type, "title": i.title, "confidence": i.confidence, "status": i.status}
            for i in get_plan(db, task.id)]
    record = VersionKnowledgeRecord(
        project_id=task.project_id,
        task_id=task.id,
        version=task.version,
        title=task.title,
        summary=task.summary or f"{task.title} 经验收（{task.verdict}）",
        coverage=json.dumps(coverage, ensure_ascii=False),
        verdict=task.verdict,
        risk=json.dumps(risk if isinstance(risk, list) else [risk], ensure_ascii=False),
        plan_summary=json.dumps(plan, ensure_ascii=False),
        defect_count=len(task.defects),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_reuse_suggestions(db: Session, project_id: int, limit: int = 5) -> list[dict]:
    """B11 复用建议：上一版知识记录 → 下版建任务自动带出。"""
    rows = (
        db.query(VersionKnowledgeRecord)
        .filter(VersionKnowledgeRecord.project_id == project_id)
        .order_by(VersionKnowledgeRecord.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        coverage = json.loads(r.coverage or "{}")
        plan = json.loads(r.plan_summary or "[]")
        out.append({
            "id": r.id, "version": r.version, "title": r.title,
            "verdict": r.verdict, "defect_count": r.defect_count,
            "pass_rate": round(
                int(coverage.get("pass", 0)) * 100 / max(sum(int(v) for v in coverage.values()), 1), 1
            ),
            "reuse": [i["title"] for i in plan if i.get("status") in ("adopted", "modified")][:10],
        })
    return out


def get_knowledge_record(db: Session, task_id: int) -> dict:
    """B11 读取版本知识记录（无则空）。"""
    rec = db.query(VersionKnowledgeRecord).filter_by(task_id=task_id).first()
    if rec is None:
        return {}
    return {
        "id": rec.id, "version": rec.version, "title": rec.title,
        "verdict": rec.verdict, "defect_count": rec.defect_count,
        "coverage": json.loads(rec.coverage or "{}"),
    }


def recommend_regression_set(db: Session, task_id: int) -> list[dict]:
    """B12 建任务即给推荐回归集：采纳方案条目 + 变更模块 + 上版复用建议（影响面）。"""
    task = get_task(db, task_id)
    plan = get_plan(db, task_id)
    adopted = [i for i in plan if i.status in ("adopted", "modified")]
    scope = json.loads(task.scope or "{}")
    modules = scope.get("modules", []) if isinstance(scope, dict) else []
    # 复用建议（上版采纳/修改条目）
    reuse = []
    for rec in get_reuse_suggestions(db, task.project_id, limit=3):
        reuse.extend(rec.get("reuse", []))
    out = []
    for i in adopted:
        out.append(
            {"kind": i.item_type, "title": i.title, "source": "方案条目",
             "priority": "P0" if i.confidence >= 70 else "P1"}
        )
    for m in modules:
        out.append(
            {"kind": "module", "title": f"{m} 回归", "source": "变更模块", "priority": "P0"}
        )
    for r in reuse[:5]:
        out.append({"kind": "reuse", "title": r, "source": "上版复用", "priority": "P1"})
    # 去重
    seen = set()
    dedup = []
    for item in out:
        key = item["title"]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    return dedup


def sync_defect_notification(db: Session, task_id: int, defect_id: int) -> dict:
    """B12 缺陷一键同步到通知/缺陷库（写 NotificationLog + 返回已同步状态）。"""
    task = get_task(db, task_id)
    linked = db.query(VersionTaskDefect).filter_by(task_id=task.id, defect_id=defect_id).first()
    if linked is None:
        # 若未关联则补一个
        link = VersionTaskDefect(task_id=task.id, defect_id=defect_id)
        db.add(link)
        db.commit()
    log = NotificationLog(project_id=task.project_id, event="defect_sync", status="sent", error=f"defect:{defect_id}")
    db.add(log)
    db.commit()
    return {"synced": True, "defect_id": defect_id}


def get_operations_metrics(db: Session, project_id: int) -> dict:
    """B13 运营指标看板：回归人天 / 提测→放行周期 / 漏测 / 周活跃（基于 version_task + knowledge_record）。"""
    tasks = db.query(VersionTask).filter(VersionTask.project_id == project_id).all()
    released = [t for t in tasks if t.status == "released"]
    # F-06：回归人天不再用「放行数量×0.5」臆造。真实人天需人工/任务录入；
    # 仅当存在真实记录字段时才取值，否则返回 recorded=False，由前端提示「人工录入」。
    recorded_days = sum(
        float(getattr(t, "regression_days", 0) or 0) for t in released
    )
    regression_person_days = round(recorded_days, 1)
    # 提测→放行周期：放行任务 created_at -> updated_at 的平均天数
    cycles = []
    for t in released:
        if t.created_at and t.updated_at:
            cycles.append(max((t.updated_at - t.created_at).total_seconds() / 86400, 0))
    avg_cycle = round(sum(cycles) / len(cycles), 1) if cycles else 0.0
    # 漏测：已放行任务关联的缺陷数（proxy）
    missed = sum(len(t.defects) for t in released)
    # 周活跃：近 7 天有更新/创建的任务数
    cutoff = _now()
    from datetime import datetime as _dt, timedelta
    cutoff = _dt.now() - timedelta(days=7)
    weekly_active = sum(1 for t in tasks if (t.updated_at or t.created_at) >= cutoff)
    return {
        "regression_person_days": regression_person_days,
        "regression_person_days_recorded": bool(recorded_days),
        "cycle_avg_days": avg_cycle,
        "missed_defects": missed,
        "weekly_active": weekly_active,
        "released_count": len(released),
        "total_tasks": len(tasks),
    }


def compare_versions(db: Session, project_id: int, version_a: str, version_b: str) -> dict:
    """B13 跨版本对比：覆盖/结论/缺陷 对比两个版本。

    优先读 B11 知识记录；未沉淀时回退到真实 ``VersionTask`` 的 coverage/verdict/defects
    （F-07），避免「无知识记录 → 不可比」。
    """
    def _row(version: str):
        rec = (
            db.query(VersionKnowledgeRecord)
            .filter_by(project_id=project_id, version=version)
            .order_by(VersionKnowledgeRecord.id.desc())
            .first()
        )
        if rec is not None:
            cov = json.loads(rec.coverage or "{}")
            total = sum(int(v) for v in cov.values()) or 1
            return {
                "version": version, "exists": True, "verdict": rec.verdict,
                "defect_count": rec.defect_count,
                "pass_rate": round(int(cov.get("pass", 0)) * 100 / total, 1),
                "coverage": cov, "source": "knowledge_record",
            }
        # F-07 回退：真实 VersionTask（取该版本最近一条）
        task = (
            db.query(VersionTask)
            .filter_by(project_id=project_id, version=version)
            .order_by(VersionTask.id.desc())
            .first()
        )
        if task is None:
            return {"version": version, "exists": False}
        cov = _to_int_dict(task.coverage)
        total = sum(int(v) for v in cov.values()) or 1
        return {
            "version": version, "exists": True, "verdict": task.verdict or "",
            "defect_count": len(task.defects),
            "pass_rate": round(int(cov.get("pass", 0)) * 100 / total, 1),
            "coverage": cov, "source": "version_task",
        }
    return {"a": _row(version_a), "b": _row(version_b)}


def list_version_knowledge(db: Session, project_id: int, limit: int = 50) -> list[dict]:
    """B11 版本知识记录（版本记录 / 复用建议 Tab 数据源）。"""
    rows = (
        db.query(VersionKnowledgeRecord)
        .filter(VersionKnowledgeRecord.project_id == project_id)
        .order_by(VersionKnowledgeRecord.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "version": r.version,
            "title": r.title,
            "summary": r.summary,
            "coverage": _to_int_dict(r.coverage),
            "verdict": r.verdict,
            "risk": _to_int_dict(r.risk),
            "plan_summary": _to_int_dict(r.plan_summary),
            "defect_count": r.defect_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
