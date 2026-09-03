"""Business onboarding service — B15 新业务接入 4 步向导 + 业务基线。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.business_onboarding import BusinessOnboarding
from app.services import openapi_import_service, version_task_service
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
    """Step 2-4：接基线 / 生成方案 / 跑基线（F-08：接入真基线、AI 方案、真实执行）。"""
    ob = get_onboarding(db, onboarding_id)
    if ob.step >= 4:
        raise APIException(code=1, msg="业务接入已完成，不能继续推进")
    if step != ob.step + 1:
        raise APIException(code=1, msg=f"请按顺序完成接入步骤，下一步应为第 {ob.step + 1} 步")
    if step == 2:
        if not ob.api_spec_url.strip():
            raise APIException(code=1, msg="请填写 OpenAPI Spec URL 后再接入基线")
        spec = openapi_import_service.resolve_openapi_spec(ob.api_spec_url)
        if not spec:
            raise APIException(code=1, msg="OpenAPI 文档读取或解析失败")
        preview = openapi_import_service.preview_openapi_import(
            spec, project_id=ob.project_id, service_name=ob.service_key
        )
        if preview["total_count"] <= 0:
            raise APIException(code=1, msg="OpenAPI 文档没有可导入的接口")
        imported = openapi_import_service.confirm_openapi_import(
            db,
            spec,
            project_id=ob.project_id,
            service_name=ob.service_key,
            source_ref=ob.api_spec_url,
            source_type="openapi_url",
        )
        endpoint_contract = [
            {
                "method": endpoint["method"],
                "path": endpoint["path"],
                "summary": endpoint.get("summary", ""),
            }
            for endpoint in preview["endpoints"]
        ]
        task = version_task_service.create_task(
            db,
            project_id=ob.project_id,
            title=f"{ob.name} 业务基线",
            version=ob.service_key,
            source="onboarding",
            scope={
                "modules": ["核心流程", "接口契约", "异常链路"],
                "base_url": ob.base_url,
                "api_spec_url": ob.api_spec_url,
                "openapi_import_batch_id": imported["batch_id"],
                "openapi_endpoint_count": imported["total_count"],
                "openapi_endpoints": endpoint_contract,
            },
        )
        ob.version_task_id = task.id
    if step == 3:
        # 生成方案：走项目级 AI（F-01），不再硬编码占位
        if not ob.version_task_id:
            raise APIException(code=1, msg="请先完成基线接入（第 2 步）")
        items = version_task_service.ai_generate_plan(db, ob.version_task_id, ob.project_id)
        if not items:
            raise APIException(code=1, msg="AI 未生成可执行的验收方案")
        for item in items:
            item.status = "adopted"
    if step == 4:
        # 跑基线：真实执行（F-02）
        if not ob.version_task_id:
            raise APIException(code=1, msg="请先完成方案生成（第 3 步）")
        run = version_task_service.start_run(db, ob.version_task_id)
        ob.baseline = json.dumps(
            {
                "task_id": ob.version_task_id,
                "run_id": run.id,
                "status": run.status,
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "blocked": run.blocked,
            },
            ensure_ascii=False,
        )
        ob.status = "active" if run.status == "done" else "blocked"
    ob.step = step
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
