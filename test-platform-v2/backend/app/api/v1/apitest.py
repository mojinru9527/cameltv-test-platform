"""接口测试 API 路由 — /api/v1/apitest/* 即时执行（不保存用例）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services.api_execution_service import quick_execute

router = APIRouter(prefix="/apitest", tags=["接口测试"])


class QuickExecuteRequest(BaseModel):
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    url: str = Field(..., min_length=1)
    headers: str = Field(default="{}")   # JSON 字符串
    body: str = Field(default="")        # JSON 字符串
    assertions: str = Field(default="[]")  # JSON 数组
    environment_id: int | None = None
    dataset_id: int | None = None


@router.post("/api-execute", response_model=R[dict], summary="即时执行（调试）")
def api_quick_execute(
    body: QuickExecuteRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """发送一个接口请求并返回响应+断言结果（不保存为用例）。"""
    import json

    request_def = {
        "method": body.method,
        "url": body.url,
        "headers": _safe_json(body.headers, {}),
        "body": body.body,
    }
    assertions = _safe_json(body.assertions, [])

    try:
        result = quick_execute(
            db, request_def,
            assertions=assertions,
            environment_id=body.environment_id,
            dataset_id=body.dataset_id,
        )
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    return R.ok(result)


def _safe_json(raw: str, default):
    import json as _json
    if not raw or not raw.strip():
        return default
    try:
        return _json.loads(raw)
    except (_json.JSONDecodeError, TypeError):
        return default
