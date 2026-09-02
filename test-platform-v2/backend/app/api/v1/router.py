"""v1 路由聚合。

Batch 181（FIX-173-P2-10）：9 个大路由文件按域拆分后在此聚合。
注册顺序保持拆分前的相对顺序（如 test_case_taxonomy 先于 test_case_crud，
避免单段字面量路由被 /{case_id} 抢匹配）。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, dashboard, dataset, defect, dsh_tasks, environment, integration, notify, open_api, open_knowledge, organization, playground, project, report, schedule, system, template, token, trace, ui_test, version_mission, agent, interaction_coverage
from app.api.v1 import ai_config
from app.api.v1 import test_case_taxonomy, test_case_crud, test_case_files
from app.api.v1 import test_plan_crud, test_plan_execution
from app.api.v1 import requirement_docs, requirement_ai, requirement_ai_generate, requirement_import
from app.api.v1 import apitest_assets, apitest_cases, apitest_tasks, api_runner
from app.api.v1 import knowledge_core, knowledge_graph, knowledge_artifacts
from app.api.v1 import wiki_core, wiki_diff, wiki_external, wiki_sync
from app.api.v1 import release_bundles_core, release_bundles_diff
from app.api.v1 import requirement_modules_core, requirement_modules_extract, requirement_modules_interactions, requirement_modules_links
from app.api.v1 import lanhu_evidence_jobs, lanhu_evidence_assets, lanhu_evidence_review
from app.api.v1 import version_task
from app.api.v1 import metrics
from app.api.v1 import convergence
from app.api.v1 import onboarding

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(defect.router)
api_router.include_router(environment.router)
api_router.include_router(project.router)
api_router.include_router(organization.router)
api_router.include_router(system.router)
# test_case：taxonomy（单段 /domains /stats /taxonomy）必须先于 crud（/{case_id}）注册
api_router.include_router(test_case_taxonomy.router)
api_router.include_router(test_case_crud.router)
api_router.include_router(test_case_files.router)
api_router.include_router(report.router)
api_router.include_router(schedule.router)
api_router.include_router(test_plan_crud.router)
api_router.include_router(test_plan_execution.router)
api_router.include_router(ui_test.router)
api_router.include_router(requirement_docs.router)
api_router.include_router(requirement_ai.router)
api_router.include_router(requirement_ai_generate.router)
api_router.include_router(requirement_import.router)
api_router.include_router(trace.router)
api_router.include_router(notify.router)
api_router.include_router(open_api.router)
api_router.include_router(open_knowledge.router)
api_router.include_router(token.router)
api_router.include_router(apitest_assets.router)
api_router.include_router(apitest_cases.router)
api_router.include_router(apitest_tasks.router)
api_router.include_router(api_runner.router)
api_router.include_router(dataset.router)
api_router.include_router(integration.router)
api_router.include_router(version_mission.router)
api_router.include_router(knowledge_core.router)
api_router.include_router(knowledge_graph.router)
api_router.include_router(knowledge_artifacts.router)
api_router.include_router(agent.router)
api_router.include_router(dsh_tasks.router)
api_router.include_router(ai_config.router)
api_router.include_router(wiki_core.router)
api_router.include_router(wiki_diff.router)
api_router.include_router(wiki_external.router)
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
api_router.include_router(playground.router)
api_router.include_router(version_task.router)
api_router.include_router(metrics.router)
api_router.include_router(convergence.router)
api_router.include_router(onboarding.router)
api_router.include_router(template.router)

