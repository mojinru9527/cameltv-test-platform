"""Wiki 编译流水线 —— 两阶段：LLM 分析(Analysis) → 确定性生成(Generation)。

阶段1：调用 LLM 把 raw source 分析为结构化 JSON（模块/需求/规则/字段/接口/连接/待审）。
阶段2：从分析结果确定性生成 Wiki 页面（source/module/requirement/rule/index）与页面链接，
       全部带来源引用，默认 review_status=pending（未审核不参与正式用例生成）。

自带 Session（由 BackgroundTasks 调度，post-commit，失败不影响主流程）。LLM 不可用时
退化为最小确定性分析，保证链路可跑通与可测试。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from app.core.db import SessionLocal
from app.models.wiki import WikiIngestJob, WikiRawSource
from app.services.knowledge.agent_orchestrator import _call_llm_sync
from app.services.knowledge.agent_prompts import build_system_prompt
from app.services.wiki import link_service, page_service

logger = logging.getLogger("wiki.ingest")


# ── 阶段1：分析 ──

def _run_analysis(raw: WikiRawSource) -> dict:
    meta = json.loads(raw.metadata_json or "{}")
    user_msg = (
        f"来源标题：{raw.title}\n"
        f"客户端范围：{meta.get('client_scope') or '未标注'}\n"
        f"immutable_version：{raw.immutable_version}\n\n"
        f"来源内容：\n{raw.content_md}"
    )
    res = _call_llm_sync(build_system_prompt("wiki_ingest"), user_msg)
    result = res.get("result")
    if isinstance(result, dict) and result.get("requirements") is not None:
        return result
    # 退化：LLM 不可用/解析失败 → 最小确定性分析，保证链路可跑
    return {
        "source_summary": (raw.content_md or "")[:200],
        "detected_modules": [raw.title] if raw.title else [],
        "requirements": [{
            "stable_key": raw.immutable_version or f"raw:{raw.id}",
            "title": raw.title or "需求",
            "module": raw.title or "",
            "description": (raw.content_md or "")[:1000],
            "client_scope": meta.get("client_scope") or [],
            "business_rules": [], "fields": [], "apis": [], "test_focus": [],
        }],
        "connections": [], "contradictions": [], "review_items": [],
        "confidence": 0.3,
        "_fallback": True,
    }


# ── 阶段2：生成（确定性）──

def _frontmatter(d: dict) -> str:
    lines = ["---"]
    for k, v in d.items():
        lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) if items else "_（无）_"


def _requirement_md(req: dict, raw: WikiRawSource) -> str:
    rules = [f"**{r.get('id','')}** {r.get('rule','')}" + (f" _(依据: {r.get('evidence')})_" if r.get("evidence") else "")
             for r in (req.get("business_rules") or [])]
    fields = [f"`{f.get('name','')}` ({f.get('location','')}, {f.get('type','')}"
              + (", 必填" if f.get("required") else "") + ")" for f in (req.get("fields") or [])]
    apis = [f"`{a.get('method','')} {a.get('path','')}`" for a in (req.get("apis") or [])]
    parts = [
        f"# {req.get('title','需求')}",
        f"> 模块：{req.get('module','') or '未分组'} · 客户端：{'/'.join(req.get('client_scope') or []) or '未标注'}",
        "",
        req.get("description", "") or "_（无描述）_",
        "\n## 业务规则", _md_list(rules),
        "\n## 字段约束", _md_list(fields),
        "\n## 关联接口", _md_list(apis),
        "\n## 测试关注点", _md_list(req.get("test_focus") or []),
        f"\n## 来源\n- Raw Source #{raw.id} · `{raw.source_ref}`",
    ]
    return "\n".join(parts)


def _generate(db, project_id: int, raw: WikiRawSource, analysis: dict) -> dict:
    src_refs = [{"raw_source_id": raw.id, "knowledge_source_id": raw.knowledge_source_id}]
    title_to_pid: dict[str, int] = {}
    pages_n = 0

    # 来源页
    src_fm = {"type": "source", "raw_source_id": raw.id, "immutable_version": raw.immutable_version}
    src_body = f"{_frontmatter(src_fm)}\n\n# 来源：{raw.title}\n\n{analysis.get('source_summary','')}\n\n- 链接：`{raw.source_ref}`"
    src_page = page_service.upsert_page(
        db, project_id=project_id, page_type="source",
        slug=page_service.slugify(f"source-{raw.immutable_version or raw.id}"),
        title=f"来源：{raw.title}", content_md=src_body, source_refs=src_refs,
        frontmatter=src_fm, confidence=float(analysis.get("confidence", 0) or 0))
    pages_n += 1

    # 模块页
    for module in (analysis.get("detected_modules") or []):
        body = f"{_frontmatter({'type': 'module', 'name': module})}\n\n# 模块：{module}"
        mp = page_service.upsert_page(
            db, project_id=project_id, page_type="module", slug=page_service.slugify(module),
            title=module, content_md=body, source_refs=src_refs, frontmatter={"type": "module"})
        title_to_pid[module] = mp.id
        pages_n += 1

    # 需求页 + 规则页
    for req in (analysis.get("requirements") or []):
        r_title = req.get("title") or "需求"
        r_body = _frontmatter({"type": "requirement", "stable_key": req.get("stable_key", "")}) + "\n\n" + _requirement_md(req, raw)
        rp = page_service.upsert_page(
            db, project_id=project_id, page_type="requirement",
            slug=page_service.slugify(req.get("stable_key") or r_title),
            title=r_title, content_md=r_body, source_refs=src_refs,
            frontmatter={"type": "requirement"},
            confidence=float(analysis.get("confidence", 0) or 0))
        title_to_pid[r_title] = rp.id
        pages_n += 1
        # 来源 → 需求
        link_service.create_link(db, project_id=project_id, from_page_id=src_page.id,
                                 to_page_id=rp.id, link_type="source_of")
        # 需求 → 模块
        mod_pid = title_to_pid.get(req.get("module", ""))
        if mod_pid:
            link_service.create_link(db, project_id=project_id, from_page_id=rp.id,
                                     to_page_id=mod_pid, link_type="mentions")
        # 规则页
        if req.get("business_rules"):
            rules_md = _frontmatter({"type": "rule", "of": r_title}) + f"\n\n# {r_title} · 业务/字段规则\n\n" + \
                _md_list([f"{x.get('id','')} {x.get('rule','')}" for x in req["business_rules"]])
            rule_page = page_service.upsert_page(
                db, project_id=project_id, page_type="rule",
                slug=page_service.slugify(f"{r_title}-rules"),
                title=f"{r_title} 规则", content_md=rules_md, source_refs=src_refs,
                frontmatter={"type": "rule"})
            pages_n += 1
            link_service.create_link(db, project_id=project_id, from_page_id=rp.id,
                                     to_page_id=rule_page.id, link_type="covers")

    # 分析给出的连接（标题能匹配到页面时建链）
    links_extra = 0
    for c in (analysis.get("connections") or []):
        fp, tp = title_to_pid.get(c.get("from", "")), title_to_pid.get(c.get("to", ""))
        if fp and tp:
            ln = link_service.create_link(
                db, project_id=project_id, from_page_id=fp, to_page_id=tp,
                link_type=(c.get("type") or "depends_on"),
                evidence={"note": c.get("evidence", "")})
            if ln:
                links_extra += 1

    # 索引页
    idx = f"{_frontmatter({'type': 'index'})}\n\n# Wiki 索引\n\n" + _md_list(sorted(title_to_pid.keys()))
    page_service.upsert_page(
        db, project_id=project_id, page_type="index", slug="wiki-index",
        title="Wiki 索引", content_md=idx, source_refs=src_refs, frontmatter={"type": "index"})
    pages_n += 1

    return {"pages": pages_n, "review_items": len(analysis.get("review_items") or [])}


# ── 主入口 ──

def run_wiki_ingest_in_new_session(project_id: int, job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(WikiIngestJob, job_id)
        if not job or job.project_id != project_id or job.status in ("cancelled", "success"):
            return
        raw = db.get(WikiRawSource, job.raw_source_id)
        if not raw:
            job.status = "failed"; job.error_message = "raw source 不存在"
            job.finished_at = datetime.now(); db.commit(); return

        job.status = "running"; job.stage = "analysis"; db.commit()
        analysis = _run_analysis(raw)
        job.analysis_json = json.dumps(analysis, ensure_ascii=False)
        job.stage = "generation"; db.commit()

        result = _generate(db, project_id, raw, analysis)
        job.result_json = json.dumps(result, ensure_ascii=False)
        job.status = "success"; job.finished_at = datetime.now()
        db.commit()
    except Exception as e:
        logger.exception("wiki ingest failed: job=%s", job_id)
        db.rollback()
        try:
            job = db.get(WikiIngestJob, job_id)
            if job:
                job.status = "failed"; job.error_message = str(e)[:500]
                job.finished_at = datetime.now(); db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
