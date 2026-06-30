"""Open API for CI/CD integration — authenticated via API Token."""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import APIException
from app.models.api_token import ApiToken
from app.schemas.common import R

router = APIRouter(prefix="/open", tags=["开放API"])


def verify_api_token(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> ApiToken:
    """Validate `Bearer tpat_xxx` against stored hashes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise APIException(code=401, msg="缺少 API Token (Authorization: Bearer tpat_xxx)", http_status=401)

    plain = authorization[len("Bearer "):]
    token_hash = hashlib.sha256(plain.encode()).hexdigest()

    row = db.scalar(
        select(ApiToken).where(ApiToken.token_hash == token_hash, ApiToken.enabled == True)
    )
    if not row:
        raise APIException(code=401, msg="无效或已禁用的 API Token", http_status=401)

    return row


@router.post("/plans/{plan_id}/trigger", response_model=R[dict], summary="CI 触发测试计划执行")
def ci_trigger_plan(
    plan_id: int,
    req: Request,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI (Jenkins/GitHub Actions) 通过 API Token 触发测试计划。

    触发后返回执行摘要。结果可通过 GET /open/runs/{run_id} 查询。
    """
    from app.models.test_plan import TestPlan, TestPlanCase, TestExecution
    from datetime import datetime, timezone

    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == token.project_id)
    )
    if not plan:
        raise APIException(code=404, msg="计划不存在")

    # Execute all cases in the plan
    pcases = db.scalars(
        select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)
    ).all()

    now = datetime.now(timezone.utc)
    executed = 0
    for pc in pcases:
        exec_row = TestExecution(
            plan_case_id=pc.id, executor_id=0, status="pending",
            actual_result="", notes=f"[CI 自动触发] token={token.name}",
            executed_at=now,
        )
        db.add(exec_row)
        pc.last_status = "pending"
        pc.last_executed_at = now
        executed += 1

    # Update token last_used
    token.last_used_at = now

    db.commit()

    # Background notification
    try:
        from app.services.notify_service import notify_sync
        notify_sync(db, token.project_id, "plan_done", {
            "plan_name": plan.name,
            "result_summary": f"CI 触发 {executed} 条用例已入队",
            "link": "",
        })
    except Exception:
        pass

    return R.ok({
        "triggered": True,
        "plan_id": plan_id,
        "plan_name": plan.name,
        "cases_queued": executed,
        "triggered_by": token.name,
    })
