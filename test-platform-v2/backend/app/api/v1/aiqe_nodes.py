"""AUD-005 / Runner 运行期：节点能力心跳。

外部 Runner 每 10–20 秒调用一次，刷新 `node_capability_manifests.last_heartbeat_at`，
避免 Preflight 的 30s 心跳窗口把在线节点判成 UNAVAILABLE。

鉴权：`X-AI-Agent-Token`（与 ExecutionJob claim 同一节点令牌），token.agent_id 必须等于路径
中的 node_id；令牌只在项目作用域内有效。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.aiqe.services import capability_registry
from app.core.db import get_db
from app.schemas.common import R
from app.services import ai_agent_service

router = APIRouter(prefix="/aiqe/nodes", tags=["AIQE Nodes"])


@router.post("/{node_id}/heartbeat", response_model=R[dict], summary="节点能力心跳")
def node_capability_heartbeat(
    node_id: str,
    x_ai_agent_token: str | None = Header(default=None, alias="X-AI-Agent-Token"),
    db: Session = Depends(get_db),
):
    if not x_ai_agent_token:
        raise HTTPException(401, "缺少 X-AI-Agent-Token")
    token = ai_agent_service.verify_agent_token(db, x_ai_agent_token)
    if token is None:
        raise HTTPException(401, "无效或已撤销的节点令牌")
    if token.agent_id != node_id:
        raise HTTPException(403, "节点令牌与 node_id 不匹配")

    try:
        row = capability_registry.heartbeat(db, node_id)
    except LookupError:
        raise HTTPException(404, f"节点能力清单不存在: {node_id}") from None
    except capability_registry.CapabilityError as exc:
        raise HTTPException(409, str(exc)) from None
    db.commit()
    effective = capability_registry.compute_effective_status(row)
    return R.ok(
        {
            "node_id": row.node_id,
            "capability_status": row.capability_status,
            "effective_status": effective,
            "verified": row.capability_status == capability_registry.CapabilityStatus.VERIFIED.value,
            "last_heartbeat_at": row.last_heartbeat_at.isoformat()
            if row.last_heartbeat_at
            else None,
            "next_heartbeat_seconds": 15,
        }
    )
