"""API Token service — 路由层禁 ORM 收敛（Batch 182 / C181-1）。

token.py / open_api.py 的 ApiToken 查询与创建收敛至此：
- 薄函数签名 `(db, ...)`，沿用调用方会话，不自行 commit（commit 保留在路由层）；
- `verify_token_hash` 供 open_api 鉴权核心（verify_api_token）复用。
"""
from __future__ import annotations

import ast
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import forbidden
from app.models.api_token import ApiToken


def parse_scopes(value: object) -> list[str]:
    """Normalize JSON and pre-Batch-127 Python-repr scope storage."""
    parsed = value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                parsed = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                parsed = []
    if not isinstance(parsed, (list, tuple)):
        return []
    return [str(scope).strip() for scope in parsed if str(scope).strip()]


def verify_token_hash(db: Session, token_hash: str) -> ApiToken | None:
    """按 token_hash 校验启用的 API Token（open_api 鉴权核心查询）。"""
    return db.scalar(
        select(ApiToken).where(ApiToken.token_hash == token_hash, ApiToken.enabled)
    )


def require_scope(token: ApiToken, scope: str) -> None:
    """Reject a valid API Token that lacks the requested least-privilege scope."""
    if scope not in parse_scopes(token.scopes):
        raise forbidden(f"API Token 缺少作用域：{scope}")


def mark_used(token: ApiToken) -> None:
    """Record successful machine-token use in the caller's transaction."""
    token.last_used_at = datetime.now(timezone.utc)


def get_token(db: Session, token_id: int, project_id: int) -> ApiToken | None:
    """项目内按 id 查询 API Token（供更新/删除复用）。"""
    return db.scalar(
        select(ApiToken).where(
            ApiToken.id == token_id, ApiToken.project_id == project_id
        )
    )


def list_tokens(db: Session, project_id: int) -> list[dict]:
    """项目下 API Token 列表（scopes 兼容旧 repr 存储）。"""
    rows = db.scalars(
        select(ApiToken).where(ApiToken.project_id == project_id)
    ).all()
    return [{
        "id": t.id, "name": t.name, "token_prefix": t.token_prefix,
        "scopes": parse_scopes(t.scopes), "enabled": t.enabled,
        "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in rows]


def create_token(db: Session, project_id: int, name: str, scopes: list[str]) -> dict:
    """创建 API Token；仅此处返回明文 token，调用方负责 commit。"""
    plain, token_hash = ApiToken.generate()
    t = ApiToken(
        project_id=project_id,
        name=name,
        token_hash=token_hash,
        token_prefix=plain[:12],
        scopes=json.dumps(scopes, ensure_ascii=False),
        enabled=True,
    )
    db.add(t)
    db.flush()
    return {
        "id": t.id,
        "name": t.name,
        "token": plain,   # ⚠️ save this now — we don't store the plain value
        "token_prefix": t.token_prefix,
        "scopes": scopes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
