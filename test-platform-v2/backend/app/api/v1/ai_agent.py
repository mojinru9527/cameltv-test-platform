"""执行节点凭据路由（平台简化批次，原「AI Agent 控制面」收敛）。

AI 本地管线（AiJob 派发/认领/上报）已删除；仅保留节点注册/令牌吊销两个端点，
供 `cameltv-node`（scripts/node）注册并获取 `X-AI-Agent-Token`。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import ai_agent_service

router = APIRouter(prefix="/ai", tags=["执行节点"])


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)


class AgentTokenRevokeRequest(BaseModel):
    token_id: int


def _project_id(current: CurrentUser) -> int:
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


@router.post("/agents/register", response_model=R[dict], summary="注册本地执行节点（签发一次性 token）")
def register_agent(
    body: AgentRegisterRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    row, plain = ai_agent_service.register_agent(
        db, body.agent_id, _project_id(current), body.capabilities
    )
    return R.ok(
        {
            "agent_id": row.agent_id,
            "status": row.status,
            "project_scope": row.project_scope,
            "token": plain,
            "token_notice": "token 仅本次返回，请立即保存到本地配置",
        }
    )


@router.post("/agents/tokens/revoke", response_model=R[dict], summary="吊销节点 Token")
def revoke_agent_token(
    body: AgentTokenRevokeRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    ok = ai_agent_service.revoke_agent_token(db, body.token_id, _project_id(current))
    if not ok:
        raise HTTPException(404, "Token 不存在或不属于当前项目")
    return R.ok({"token_id": body.token_id, "enabled": False})
