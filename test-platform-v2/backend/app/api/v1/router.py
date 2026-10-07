"""v1 路由聚合（平台简化批次：删除域已摘除）。

保留：认证/工作台/项目/系统/用例/计划(只读)/缺陷/需求(AI生成)/接口测试/UI 自动化/
环境/定时/版本验收任务/发布包/项目知识库/蓝湖证据/AI 配置/执行节点协议/影响面。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    dashboard,
    defect,
    environment,
    execution_jobs,
    impact,
    open_api,
    project,
    schedule,
    system,
    token,
    ui_test,
    interaction_coverage,
)
from app.api.v1 import ai_config
from app.api.v1 import ai_agent
from app.api.v1 import test_case_taxonomy, test_case_crud, test_case_files
from app.api.v1 import test_plan_crud, test_plan_execution
from app.api.v1 import requirement_docs, requirement_ai, requirement_ai_generate, requirement_import
from app.api.v1 import apitest_assets, apitest_cases, apitest_tasks, api_runner
from app.api.v1 import knowledge_core
from app.api.v1 import wiki_core, wiki_sync
from app.api.v1 import release_bundles_core, release_bundles_diff
from app.api.v1 import (
    requirement_modules_core,
    requirement_modules_extract,
    requirement_modules_interactions,
    requirement_modules_links,
)
from app.api.v1 import lanhu_evidence_jobs, lanhu_evidence_assets, lanhu_evidence_review
from app.api.v1 import version_task
from app.modules.campaign_execution import router as campaign_execution_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(defect.router)
api_router.include_router(environment.router)
api_router.include_router(project.router)
api_router.include_router(system.router)
# test_case：taxonomy（单段 /domains /stats /taxonomy）必须先于 crud（/{case_id}）注册
api_router.include_router(test_case_taxonomy.router)
api_router.include_router(test_case_crud.router)
api_router.include_router(test_case_files.router)
api_router.include_router(schedule.router)
api_router.include_router(test_plan_crud.router)
api_router.include_router(test_plan_execution.router)
api_router.include_router(ui_test.router)
api_router.include_router(requirement_docs.router)
api_router.include_router(requirement_ai.router)
api_router.include_router(requirement_ai_generate.router)
api_router.include_router(requirement_import.router)
api_router.include_router(open_api.router)
api_router.include_router(token.router)
api_router.include_router(apitest_assets.router)
api_router.include_router(apitest_cases.router)
api_router.include_router(apitest_tasks.router)
api_router.include_router(api_runner.router)
api_router.include_router(knowledge_core.router)
api_router.include_router(ai_config.router)
api_router.include_router(ai_agent.router)
api_router.include_router(execution_jobs.router)
api_router.include_router(impact.router)
api_router.include_router(wiki_core.router)
api_router.include_router(wiki_sync.router)
api_router.include_router(release_bundles_core.router)
api_router.include_router(release_bundles_diff.router)
api_router.include_router(requirement_modules_core.router)
api_router.include_router(requirement_modules_extract.router)
api_router.include_router(requirement_modules_interactions.router)
api_router.include_router(requirement_modules_links.router)
api_router.include_router(interaction_coverage.router)
api_router.include_router(lanhu_evidence_jobs.router)
api_router.include_router(lanhu_evidence_assets.router)
api_router.include_router(lanhu_evidence_review.router)
api_router.include_router(version_task.router)
api_router.include_router(campaign_execution_router.router)
