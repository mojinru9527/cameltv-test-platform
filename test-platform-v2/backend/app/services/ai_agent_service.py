"""执行节点凭据服务（平台简化批次，原「本地 AI Agent 控制面」收敛）。

AI 本地管线（AiJob 派发/认领/上报）已随简化批次删除；本文件只保留**节点凭据**
三函数——`cameltv-node` 本地执行节点（scripts/node）与 ExecutionJob 协议
（`X-AI-Agent-Token` 鉴权，见 api/v1/execution_jobs.py）依赖它们。
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_agent_token import AiAgentToken
from app.models.ai_job import AiAgent

logger = logging.getLogger("ai.agent")

AGENT_TOKEN_PREFIX = "agt_"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


# ── Agent 注册与凭据 ────────────────────────────────────────────

def register_agent(
    db: Session,
    agent_id: str,
    project_scope: int,
    capabilities: list[str],
    *,
    issue_token: bool = True,
) -> tuple[AiAgent, str | None]:
    """注册/更新节点；默认签发一次性明文 token（仅本次返回）。"""
    row = db.scalar(select(AiAgent).where(AiAgent.agent_id == agent_id))
    if row is None:
        row = AiAgent(agent_id=agent_id)
        db.add(row)
    row.project_scope = project_scope
    row.capabilities_json = json.dumps(capabilities, ensure_ascii=False)
    row.status = "online"
    row.last_health_at = _now()

    plain: str | None = None
    if issue_token:
        plain = f"{AGENT_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        db.add(
            AiAgentToken(
                project_id=project_scope,
                agent_id=agent_id,
                name=f"{agent_id}-token",
                token_hash=_hash_token(plain),
                token_prefix=plain[:12],
                enabled=True,
            )
        )
    db.commit()
    db.refresh(row)
    return row, plain


def verify_agent_token(db: Session, plain: str) -> AiAgentToken | None:
    if not plain:
        return None
    token = db.scalar(select(AiAgentToken).where(AiAgentToken.token_hash == _hash_token(plain)))
    if token is None or not token.enabled or token.revoked_at is not None:
        return None
    token.last_used_at = _now()
    db.commit()
    db.refresh(token)
    return token


def revoke_agent_token(db: Session, token_id: int, project_id: int) -> bool:
    token = db.scalar(
        select(AiAgentToken).where(AiAgentToken.id == token_id, AiAgentToken.project_id == project_id)
    )
    if token is None:
        return False
    token.enabled = False
    token.revoked_at = _now()
    db.commit()
    return True
