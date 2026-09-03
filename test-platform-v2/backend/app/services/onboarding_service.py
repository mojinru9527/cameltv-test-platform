"""Business onboarding service — B15 新业务接入 4 步向导 + 业务基线。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_onboarding import BusinessOnboarding
from app.models.requirement import RequirementDocument
from app.models.version_task import VersionTask
from app.services import openapi_import_service, version_task_service
from app.core.exceptions import APIException, not_found


def create_onboarding(
    db: Session, project_id: int, *, name: str, service_key: str,
    version: str = "", requirement_text: str = "",
    api_spec_url: str = "", base_url: str = "",
) -> BusinessOnboarding:
    """Step 1 登记业务。"""
    ob = BusinessOnboarding(
        project_id=project_id, name=name, service_key=service_key,
        version=version, requirement_text=requirement_text,
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
        task_version = ob.version or ob.service_key
        task = db.scalar(
            select(VersionTask).where(
                VersionTask.project_id == ob.project_id,
                VersionTask.version == task_version,
            )
        )
        task_requirement = (
            db.get(RequirementDocument, task.requirement_doc_id)
            if task is not None and task.requirement_doc_id
            else None
        )
        if task_requirement and task_requirement.content.strip() != ob.requirement_text.strip():
            raise APIException(
                code=1,
                msg=f"当前项目已有 {task_version} 版本任务，且绑定了不同的需求内容",
            )

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
        scope = {
            "modules": ["核心流程", "接口契约", "异常链路"],
            "base_url": ob.base_url,
            "api_spec_url": ob.api_spec_url,
            "openapi_import_batch_id": imported["batch_id"],
            "openapi_endpoint_count": imported["total_count"],
            "openapi_endpoints": endpoint_contract,
        }
        if task is not None:
            if task_requirement is None:
                from app.services import requirement_service

                created = requirement_service.create_requirement(
                    db,
                    project_id=ob.project_id,
                    title=f"{ob.name} {ob.version} 接入需求".strip(),
                    file_type="manual",
                    source_ref="onboarding",
                    content=ob.requirement_text,
                    commit=False,
                )
                task.requirement_doc_id = created["id"]
            try:
                existing_scope = json.loads(task.scope or "{}")
            except (TypeError, ValueError):
                existing_scope = {}
            existing_scope.update({key: value for key, value in scope.items() if key != "modules"})
            task.scope = json.dumps(existing_scope, ensure_ascii=False)
        else:
            from app.services import requirement_service

            requirement = requirement_service.create_requirement(
                db,
                project_id=ob.project_id,
                title=f"{ob.name} {ob.version} 接入需求".strip(),
                file_type="manual",
                source_ref="onboarding",
                content=ob.requirement_text,
                commit=False,
            )
            task = version_task_service.create_task(
                db,
                project_id=ob.project_id,
                title=f"{ob.name} {ob.version} 业务基线".strip(),
                version=task_version,
                source="onboarding",
                requirement_doc_id=requirement["id"],
                scope=scope,
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


def get_readiness(db: Session, project_id: int) -> dict:
    """汇总已有事实；不发外部探测，也不在请求内启动基础设施。"""
    from app.modules.aitde.common.enums import WorkerStatus
    from app.modules.aitde.workflow import repository
    from app.modules.aitde.workflow.gateway import temporal_gateway
    from app.services.ai_config_service import ai_config_service

    ai = ai_config_service.resolve_out(db, project_id)
    health = ai.get("health") or {}
    health_status = str(health.get("status") or "unknown")
    ai_ready = bool(ai.get("configured")) and health_status == "ok"
    if not ai.get("configured"):
        ai_status = "blocked"
        ai_message = "尚未配置 AI 提供方"
    elif health_status == "ok":
        ai_status = "ready"
        ai_message = str(health.get("message") or "最近一次真实调用成功")
    elif health_status == "error":
        ai_status = "blocked"
        ai_message = str(health.get("message") or "最近一次真实调用失败")
    else:
        ai_status = "unknown"
        ai_message = "已配置，但尚未完成真实连通性验证"

    temporal_code, _ = temporal_gateway.unavailable()
    temporal_ready = temporal_code is None

    repository.mark_offline_workers(db)
    workers = repository.list_workers(db)
    online_workers = [row for row in workers if row.status == WorkerStatus.ONLINE.value]
    worker_ready = bool(online_workers)

    return {
        "project_id": project_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "baseline_ready": ai_ready,
        "durable_ready": ai_ready and temporal_ready and worker_ready,
        "services": {
            "ai_provider": {
                "status": ai_status,
                "message": ai_message,
                "managed_by": "project_admin",
                "provider": ai.get("provider"),
            },
            "temporal": {
                "status": "ready" if temporal_ready else "blocked",
                "message": (
                    "耐久运行已配置，由平台常驻管理"
                    if temporal_ready
                    else "耐久运行未启用；B15 基线可继续，AITDE 耐久执行需管理员处理"
                ),
                "managed_by": "platform",
            },
            "runtime_worker": {
                "status": "ready" if worker_ready else "blocked",
                "message": (
                    f"{len(online_workers)} 个执行节点在线"
                    if worker_ready
                    else "没有在线执行节点；AITDE 耐久执行需管理员处理"
                ),
                "managed_by": "platform",
                "online_count": len(online_workers),
            },
        },
    }
