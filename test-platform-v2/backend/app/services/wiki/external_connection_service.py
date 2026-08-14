"""外部 LLM-Wiki 连接 CRUD 服务 —— 项目作用域查询/创建薄函数。

Batch 181（FIX-173-P2-10）路由拆分：wiki_external 路由层的
ExternalWikiConnection ORM 查询收敛至此，沿用调用方会话。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.wiki import ExternalWikiConnection


def get_external_connection(db: Session, conn_id: int, project_id: int) -> ExternalWikiConnection | None:
    """项目作用域内获取外部 Wiki 连接。"""
    conn = db.get(ExternalWikiConnection, conn_id)
    if not conn or conn.project_id != project_id:
        return None
    return conn


def list_external_connections(db: Session, project_id: int) -> list[ExternalWikiConnection]:
    """列出项目的外部 Wiki 连接（按 id 倒序）。"""
    return db.query(ExternalWikiConnection).filter(
        ExternalWikiConnection.project_id == project_id,
    ).order_by(ExternalWikiConnection.id.desc()).all()


def create_external_connection(
    db: Session,
    *,
    project_id: int,
    name: str,
    provider: str,
    base_url: str,
    token_encrypted: str | None,
    external_project_id: str | None,
    enabled: bool,
) -> ExternalWikiConnection:
    """创建外部 Wiki 连接并 flush（沿用调用方会话，提交由路由层负责）。"""
    conn = ExternalWikiConnection(
        project_id=project_id,
        name=name,
        provider=provider,
        base_url=base_url,
        token_encrypted=token_encrypted,
        external_project_id=external_project_id,
        enabled=enabled,
    )
    db.add(conn)
    db.flush()
    return conn
