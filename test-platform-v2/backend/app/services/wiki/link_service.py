"""Wiki 链接服务 —— 页面级链接建立（去重）与图谱同步（可选）。"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.wiki import WikiLink


def create_link(
    db: Session, *, project_id: int, from_page_id: int, to_page_id: int,
    link_type: str = "mentions", evidence: dict | None = None, confidence: float = 0.0,
) -> WikiLink | None:
    """建一条页面链接；同 (from,to,type) 已存在则跳过返回 None。自链接忽略。"""
    if from_page_id == to_page_id:
        return None
    exists = db.scalar(
        select(WikiLink.id).where(
            WikiLink.project_id == project_id,
            WikiLink.from_page_id == from_page_id,
            WikiLink.to_page_id == to_page_id,
            WikiLink.link_type == link_type,
        )
    )
    if exists:
        return None
    row = WikiLink(
        project_id=project_id, from_page_id=from_page_id, to_page_id=to_page_id,
        link_type=link_type, confidence=confidence,
        evidence_json=json.dumps(evidence or {}, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return row
