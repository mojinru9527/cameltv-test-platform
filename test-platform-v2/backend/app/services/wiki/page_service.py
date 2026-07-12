"""Wiki 页面服务 —— 版本化 upsert、审核、列表、详情、关键词检索。

约定：函数只 `db.flush()`，由调用方 commit（编译流水线自带 Session）。
版本化规则：同 (project_id, page_type, slug) 视为同一页面；
  - 内容未变（content_hash 相同）→ 不动；
  - 已 approved → 旧版置 superseded，新建 version+1 的 pending 版本（不覆盖审核结论）；
  - draft/pending/rejected → 原地更新内容，version+1，回到 pending。
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.wiki import WikiLink, WikiPage


def slugify(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[\s/\\]+", "-", s)
    s = re.sub(r"[^0-9a-z一-鿿\-]+", "", s)
    return s.strip("-")[:120] or "page"


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def upsert_page(
    db: Session,
    *,
    project_id: int,
    page_type: str,
    slug: str,
    title: str,
    content_md: str,
    source_refs: list | None = None,
    frontmatter: dict | None = None,
    confidence: float = 0.0,
    agent_run_id: int | None = None,
) -> WikiPage:
    """建/版本化一个 Wiki 页面，返回当前活跃版本。"""
    chash = _hash(content_md)
    existing = db.scalar(
        select(WikiPage).where(
            WikiPage.project_id == project_id,
            WikiPage.page_type == page_type,
            WikiPage.slug == slug,
            WikiPage.review_status != "superseded",
        ).order_by(WikiPage.version.desc())
    )

    def _new(version: int) -> WikiPage:
        row = WikiPage(
            project_id=project_id, page_type=page_type, slug=slug, title=title,
            content_md=content_md, content_hash=chash, version=version,
            review_status="pending", confidence=confidence,
            source_refs_json=json.dumps(source_refs or [], ensure_ascii=False),
            frontmatter_json=json.dumps(frontmatter or {}, ensure_ascii=False),
            created_by_agent_run_id=agent_run_id,
        )
        db.add(row)
        db.flush()
        return row

    if existing is None:
        return _new(1)
    if existing.content_hash == chash:
        return existing  # 内容未变
    if existing.review_status == "approved":
        existing.review_status = "superseded"
        db.flush()
        return _new(existing.version + 1)
    # draft/pending/rejected → 原地更新
    existing.title = title
    existing.content_md = content_md
    existing.content_hash = chash
    existing.version = existing.version + 1
    existing.review_status = "pending"
    existing.confidence = confidence
    existing.source_refs_json = json.dumps(source_refs or [], ensure_ascii=False)
    existing.frontmatter_json = json.dumps(frontmatter or {}, ensure_ascii=False)
    db.flush()
    return existing


def list_pages(
    db: Session, project_id: int, *,
    page_type: str | None = None, review_status: str | None = None,
    keyword: str | None = None, page: int = 1, page_size: int = 50,
) -> tuple[list[WikiPage], int]:
    base = select(WikiPage).where(
        WikiPage.project_id == project_id, WikiPage.review_status != "superseded")
    cnt = select(func.count(WikiPage.id)).where(
        WikiPage.project_id == project_id, WikiPage.review_status != "superseded")
    if page_type:
        base = base.where(WikiPage.page_type == page_type)
        cnt = cnt.where(WikiPage.page_type == page_type)
    if review_status:
        base = base.where(WikiPage.review_status == review_status)
        cnt = cnt.where(WikiPage.review_status == review_status)
    if keyword:
        kw = f"%{keyword}%"
        base = base.where(or_(WikiPage.title.like(kw), WikiPage.content_md.like(kw)))
        cnt = cnt.where(or_(WikiPage.title.like(kw), WikiPage.content_md.like(kw)))
    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(db.scalars(
        base.order_by(WikiPage.page_type, WikiPage.id.desc())
        .offset((page - 1) * page_size).limit(page_size)).all())
    return rows, total


def get_page(db: Session, page_pk: int, project_id: int) -> WikiPage | None:
    row = db.get(WikiPage, page_pk)
    if not row or row.project_id != project_id:
        return None
    return row


def review_page(db: Session, page_pk: int, project_id: int, *, approve: bool) -> WikiPage | None:
    row = get_page(db, page_pk, project_id)
    if not row:
        return None
    row.review_status = "approved" if approve else "rejected"
    db.flush()
    return row


def get_page_links(db: Session, page_pk: int, project_id: int) -> list[WikiLink]:
    return list(db.scalars(
        select(WikiLink).where(
            WikiLink.project_id == project_id,
            or_(WikiLink.from_page_id == page_pk, WikiLink.to_page_id == page_pk),
        )).all())
