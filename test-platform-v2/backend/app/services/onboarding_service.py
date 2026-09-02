"""Business onboarding service — B15 新业务接入 4 步向导 + 业务基线。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.business_onboarding import BusinessOnboarding
from app.services import version_task_service
from app.core.exceptions import APIException, not_found


def create_onboarding(
    db: Session, project_id: int, *, name: str, service_key: str,
    api_spec_url: str = "", base_url: str = "",
) -> BusinessOnboarding:
    """Step 1 登记业务。"""
    ob = BusinessOnboarding(
        project_id=project_id, name=name, service_key=service_key,
        api_spec_url=api_spec_url, base_url=base_url, status="onboarding", step=1,
    )
    db.add(ob)
    db.commit()
    db.refresh(ob)
    return ob


def get_onboarding(db: Session, onboarding_id: int) -> BusinessOnboarding:
    ob = db.get(BusinessOnboarding, onboarding_id)
    if ob is None:
        raise not_found("接入记录不存在")
    return ob


def complete_step(db: Session, onboarding_id: int, step: int) -> BusinessOnboarding:
    """Step 2-4：接基线 / 生成方案 / 跑基线。"""
    ob = get_onboarding(db, onboarding_id)
    if step < ob.step:
        raise APIException(code=1, msg="步骤已推进")
    ob.step = step
    if step == 3:
        # 生成版本验收任务 + 方案条目（业务基线）
        task = version_task_service.create_task(
            db, project_id=ob.project_id, title=f"{ob.name} 业务基线", version=ob.service_key, source="onboarding"
        )
        ob.version_task_id = task.id
        items = []
        for scope in ["核心流程", "接口契约", "异常链路"]:
            items.append({"item_type": "functional", "title": f"{ob.name}-{scope}", "confidence": 75})
        version_task_service.generate_plan(db, task.id, items)
    if step == 4:
        # 跑基线
        if not ob.version_task_id:
            raise APIException(code=1, msg="请先完成方案生成（第 3 步）")
        run = version_task_service.start_run(db, ob.version_task_id)
        ob.baseline = json.dumps(
            {"task_id": ob.version_task_id, "run_id": run.id, "passed": run.passed, "failed": run.failed},
            ensure_ascii=False,
        )
        ob.status = "active"
    db.commit()
    db.refresh(ob)
    return ob


def list_onboardings(db: Session, project_id: int) -> list[BusinessOnboarding]:
    return (
        db.query(BusinessOnboarding)
        .filter(BusinessOnboarding.project_id == project_id)
        .order_by(BusinessOnboarding.id.desc())
        .all()
    )
