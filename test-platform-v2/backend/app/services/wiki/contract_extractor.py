"""需求契约抽取 —— 把一侧知识库中「同一需求」抽成统一契约 JSON，供差异比对。

平台 RAG：按关键词命中 KnowledgeChunk 汇总文本；平台 Wiki：命中 requirement/rule 页面。
再用 LLM 归一化为需求契约（§6.6）；LLM 不可用时退化为最小契约（保证链路可跑与可测）。
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk
from app.models.wiki import WikiPage
from app.services.knowledge.agent_orchestrator import _call_llm_sync
from app.services.knowledge.agent_prompts import build_system_prompt

logger = logging.getLogger("wiki.contract")

_EMPTY_CONTRACT_KEYS = (
    "business_rules", "fields", "apis", "acceptance_criteria",
    "exception_paths", "test_cases", "client_scope", "source_refs",
)


def _gather_rag_text(db: Session, project_id: int, query: str, top_k: int = 12) -> tuple[str, list]:
    kw = f"%{query}%"
    rows = list(db.scalars(
        select(KnowledgeChunk).where(
            KnowledgeChunk.project_id == project_id,
            KnowledgeChunk.status == "active",
            or_(KnowledgeChunk.title.like(kw), KnowledgeChunk.content.like(kw)),
        ).order_by(KnowledgeChunk.id.desc()).limit(top_k)
    ).all())
    text = "\n\n".join(f"[{r.chunk_type}] {r.title}\n{r.content}" for r in rows)
    refs = [{"chunk_id": r.id, "source_id": r.source_id} for r in rows]
    return text, refs


def _gather_wiki_text(db: Session, project_id: int, query: str, top_k: int = 12) -> tuple[str, list]:
    kw = f"%{query}%"
    rows = list(db.scalars(
        select(WikiPage).where(
            WikiPage.project_id == project_id,
            WikiPage.review_status != "superseded",
            WikiPage.page_type.in_(("requirement", "rule", "module", "api")),
            or_(WikiPage.title.like(kw), WikiPage.content_md.like(kw)),
        ).order_by(WikiPage.id.desc()).limit(top_k)
    ).all())
    text = "\n\n".join(f"[{r.page_type}] {r.title}\n{r.content_md}" for r in rows)
    refs = [{"wiki_page_id": r.id, "page_type": r.page_type} for r in rows]
    return text, refs


def _normalize_contract(raw: dict, *, title: str, source_refs: list) -> dict:
    contract = {
        "requirement_key": raw.get("requirement_key") or title,
        "title": raw.get("title") or title,
        "module": raw.get("module", ""),
        "summary": raw.get("summary", ""),
    }
    for k in _EMPTY_CONTRACT_KEYS:
        contract[k] = raw.get(k) or []
    contract["source_refs"] = source_refs
    return contract


def extract_contract(db: Session, project_id: int, *, kb_type: str, query: str) -> dict:
    """从指定知识库抽取需求契约。kb_type: platform_rag | platform_wiki。"""
    if kb_type == "platform_wiki":
        text, refs = _gather_wiki_text(db, project_id, query)
    else:
        text, refs = _gather_rag_text(db, project_id, query)

    if not text.strip():
        return _normalize_contract({"summary": "（该知识库未找到相关内容）"}, title=query, source_refs=refs)

    prompt = build_system_prompt("knowledge_diff") + (
        "\n\n## 契约抽取子任务\n把下面的知识片段归一化为一个「需求契约」JSON，字段："
        "requirement_key,title,module,summary,client_scope[],business_rules[{id,rule,evidence}],"
        "fields[{name,location,type,required}],apis[{method,path}],acceptance_criteria[],"
        "exception_paths[],test_cases[]。只依据片段，不编造。"
    )
    res = _call_llm_sync(prompt, f"需求关键词：{query}\n\n知识片段：\n{text}")
    result = res.get("result")
    if isinstance(result, dict):
        return _normalize_contract(result, title=query, source_refs=refs)
    # 退化：LLM 不可用 → 最小契约（summary 保留片段，便于人工判断）
    logger.info("contract LLM fallback: kb=%s query=%s err=%s", kb_type, query, res.get("error"))
    return _normalize_contract({"summary": text[:800]}, title=query, source_refs=refs)
