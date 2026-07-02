"""v1 路由聚合。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, av_check, dashboard, dataset, defect, environment, integration, notify, open_api, project, report, requirement, schedule, system, test_case, test_plan, token, trace, ui_test, apitest

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(defect.router)
api_router.include_router(environment.router)
api_router.include_router(project.router)
api_router.include_router(system.router)
api_router.include_router(test_case.router)
api_router.include_router(report.router)
api_router.include_router(schedule.router)
api_router.include_router(test_plan.router)
api_router.include_router(av_check.router)
api_router.include_router(ui_test.router)
api_router.include_router(requirement.router)
api_router.include_router(trace.router)
api_router.include_router(notify.router)
api_router.include_router(open_api.router)
api_router.include_router(token.router)
api_router.include_router(apitest.router)
api_router.include_router(dataset.router)
api_router.include_router(integration.router)
