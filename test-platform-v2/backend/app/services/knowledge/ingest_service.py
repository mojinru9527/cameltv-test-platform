"""事件入库 —— 把领域事件（需求/接口导入/用例/缺陷/执行失败）沉淀为知识源+切片。

设计原则（务必遵守）：
- 每个函数**自带 Session**（`SessionLocal()`），try/except 静默失败，绝不进主请求事务；
  这样入库失败永远不会回滚用户的主操作，也不会抛异常打断响应。
- 由调用方在主流程 commit 之后，经 `BackgroundTasks.add_task(...)` 调度（见各路由）。
- 入库前统一 `sanitize()` 脱敏；总开关 `knowledge_ingest_enabled` 关闭时直接跳过。
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeSource
from app.services.knowledge import chunk_service
from app.services.knowledge.sanitize import sanitize
from app.services.knowledge.source_service import record_source
from app.services.knowledge.vectorize import embed_pending_chunks_in_new_session
from app.services.knowledge.entity_service import extract_and_build_graph_in_new_session
from app.services.knowledge.change_detector import handle_changes as _auto_trigger_agents

logger = logging.getLogger("knowledge.ingest")

_MAX_RAW = 20000  # 单条 raw_content 上限，避免超大文档撑爆


def _post_ingest_hooks(project_id: int, source_id: int | None = None) -> None:
    """入库后统一触发：向量嵌入 + 实体提取 + Agent 自动变更检测（均独立 Session，不阻塞）。"""
    embed_pending_chunks_in_new_session(project_id, source_id=source_id)
    if settings.knowledge_graph_enabled:
        extract_and_build_graph_in_new_session(project_id, source_id=source_id, max_chunks=50)
    if settings.knowledge_graph_enabled:
        # 自动触发 Agent（变更检测 → 匹配规则 → 防抖）
        _auto_trigger_agents(project_id, auto_trigger=settings.knowledge_graph_enabled)


def _truncate(text: str) -> str:
    text = text or ""
    return text if len(text) <= _MAX_RAW else text[:_MAX_RAW] + "\n…(截断)"


# ── 1. 需求文档 ──

def ingest_requirement_in_new_session(project_id: int, doc_id: int) -> None:
    if not settings.knowledge_ingest_enabled:
        return
    db = SessionLocal()
    try:
        from app.models.requirement import RequirementDocument

        doc = db.get(RequirementDocument, doc_id)
        if not doc:
            return
        raw = sanitize(_truncate(doc.content))
        src = record_source(
            db,
            project_id=project_id,
            source_type="requirement",
            source_id=doc_id,
            title=doc.title or f"需求文档 #{doc_id}",
            source_ref=doc.source_ref or "",
            raw_content=raw,
            version=doc.file_type or "",
            metadata={"file_type": doc.file_type, "status": doc.status},
        )
        if src is None:
            db.commit()
            return
        chunks = [
            {"chunk_type": "requirement_rule", "title": f"{doc.title} #{i + 1}", "content": part}
            for i, part in enumerate(chunk_service.slice_text(raw))
        ]
        chunk_service.make_chunks(db, src, chunks)
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
    except Exception:
        logger.exception("ingest requirement doc_id=%s failed", doc_id)
        db.rollback()
    finally:
        db.close()


# ── 2. Swagger/OpenAPI 导入 ──

def ingest_api_import_in_new_session(project_id: int, batch_id: int, service_name: str = "") -> None:
    if not settings.knowledge_ingest_enabled:
        return
    db = SessionLocal()
    try:
        from app.models.api_asset import ApiEndpoint, ApiImportBatch

        batch = db.get(ApiImportBatch, batch_id)
        endpoints = list(
            db.scalars(
                select(ApiEndpoint).where(
                    ApiEndpoint.project_id == project_id,
                    ApiEndpoint.import_batch_id == batch_id,
                )
            ).all()
        )
        if not endpoints:
            return
        summary_lines = [f"{e.method} {e.path} {e.summary}".strip() for e in endpoints]
        raw = sanitize(_truncate("\n".join(summary_lines)))
        src = record_source(
            db,
            project_id=project_id,
            source_type="openapi",
            source_id=batch_id,
            title=f"接口导入 {service_name or ''} 批次#{batch_id}".strip(),
            source_ref=(batch.source_ref if batch else "") or "",
            raw_content=raw,
            version=(batch.version if batch else "") or "",
            metadata={"service_name": service_name, "endpoint_count": len(endpoints)},
        )
        if src is None:
            db.commit()
            return
        chunks = []
        for e in endpoints:
            body = "\n".join(
                filter(None, [
                    f"{e.method} {e.path}",
                    e.summary,
                    e.description,
                    f"request_schema: {e.request_schema}",
                    f"response_schema: {e.response_schema}",
                ])
            )
            chunks.append({
                "chunk_type": "api_schema",
                "title": f"{e.method} {e.path}",
                "content": sanitize(body),
                "tags": [service_name, e.module] if service_name else [e.module],
            })
        chunk_service.make_chunks(db, src, chunks)
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
    except Exception:
        logger.exception("ingest api import batch_id=%s failed", batch_id)
        db.rollback()
    finally:
        db.close()


# ── 3. 接口用例（仅 case_type == api） ──

def _ingest_one_test_case(db, project_id: int, case_id: int) -> None:
    """在给定 Session 内入库单条接口用例（不管理 Session、不 commit）。"""
    from app.models.test_case import TestCase

    case = db.get(TestCase, case_id)
    if not case or case.case_type != "api":
        return
    body = "\n".join(
        filter(None, [
            case.title,
            f"{case.api_method} {case.api_endpoint}".strip(),
            f"前置条件: {case.preconditions}" if case.preconditions else "",
            f"步骤: {case.steps}" if case.steps else "",
            f"断言: {case.api_assertions}" if case.api_assertions else "",
            f"预期: {case.expected_result}" if case.expected_result else "",
        ])
    )
    raw = sanitize(_truncate(body))
    src = record_source(
        db,
        project_id=project_id,
        source_type="test_case",
        source_id=case_id,
        title=case.title or f"接口用例 #{case_id}",
        source_ref=f"{case.api_method} {case.api_endpoint}".strip(),
        raw_content=raw,
        metadata={"case_id": case.case_id, "source": case.source, "priority": case.priority},
    )
    if src is None:
        return
    chunk_service.make_chunks(db, src, [{
        "chunk_type": "test_case",
        "title": case.title or f"接口用例 #{case_id}",
        "content": raw,
        "tags": [case.module, case.priority],
    }])


def ingest_test_case_in_new_session(project_id: int, case_id: int) -> None:
    if not settings.knowledge_ingest_enabled:
        return
    db = SessionLocal()
    try:
        _ingest_one_test_case(db, project_id, case_id)
        db.commit()
        _post_ingest_hooks(project_id)
    except Exception:
        logger.exception("ingest test_case case_id=%s failed", case_id)
        db.rollback()
    finally:
        db.close()


def ingest_test_cases_in_new_session(project_id: int, case_ids: list[int]) -> None:
    """批量入库多条接口用例（生成路径一次产出多条，复用单个 Session）。"""
    if not settings.knowledge_ingest_enabled or not case_ids:
        return
    db = SessionLocal()
    try:
        for cid in case_ids:
            _ingest_one_test_case(db, project_id, cid)
        db.commit()
        _post_ingest_hooks(project_id)
    except Exception:
        logger.exception("ingest test_cases (%d) failed", len(case_ids))
        db.rollback()
    finally:
        db.close()


# ── 4. 缺陷（创建/关闭） ──

def ingest_defect_in_new_session(project_id: int, defect_id: int) -> None:
    if not settings.knowledge_ingest_enabled:
        return
    db = SessionLocal()
    try:
        from app.models.defect import Defect, DefectTransition

        defect = db.get(Defect, defect_id)
        if not defect:
            return
        # 关闭时附带最新处理说明
        resolution = ""
        if defect.status in ("closed", "rejected", "resolved", "wontfix"):
            last = db.scalar(
                select(DefectTransition)
                .where(DefectTransition.defect_id == defect_id)
                .order_by(DefectTransition.id.desc())
            )
            resolution = (last.comment if last else "") or ""
        body = "\n".join(
            filter(None, [
                f"[{defect.severity}] {defect.title}",
                defect.description,
                f"状态: {defect.status}",
                f"处理说明: {resolution}" if resolution else "",
            ])
        )
        raw = sanitize(_truncate(body))
        src = record_source(
            db,
            project_id=project_id,
            source_type="defect",
            source_id=defect_id,
            title=defect.title or f"缺陷 #{defect_id}",
            source_ref=defect.defect_id or "",
            raw_content=raw,
            metadata={"severity": defect.severity, "status": defect.status, "case_id": defect.case_id},
        )
        if src is None:
            db.commit()
            return
        chunk_service.make_chunks(db, src, [{
            "chunk_type": "defect_case",
            "title": defect.title or f"缺陷 #{defect_id}",
            "content": raw,
            "tags": [defect.severity, defect.status],
        }])
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
    except Exception:
        logger.exception("ingest defect defect_id=%s failed", defect_id)
        db.rollback()
    finally:
        db.close()


# ── 5. 执行失败摘要（任务级聚合） ──

def ingest_execution_failure_in_new_session(project_id: int, task_id: int) -> None:
    if not settings.knowledge_ingest_enabled:
        return
    db = SessionLocal()
    try:
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.environment import Environment

        task = db.get(ApiExecutionTask, task_id)
        if not task:
            return
        # 生产环境结果需显式开关放行（文档 §17.2）
        if task.environment_id:
            env = db.get(Environment, task.environment_id)
            if env and env.env_type == "prod" and not settings.knowledge_ingest_production_data:
                logger.info("skip prod execution ingest task_id=%s (flag off)", task_id)
                return

        failed_items = list(
            db.scalars(
                select(ApiExecutionTaskItem).where(
                    ApiExecutionTaskItem.task_id == task_id,
                    ApiExecutionTaskItem.status == "failed",
                )
            ).all()
        )
        if not failed_items:
            return
        lines = [f"任务: {task.name or task.task_id} 失败 {len(failed_items)} 项"]
        for it in failed_items[:50]:
            snippet = it.error_message or it.assertion_results or ""
            lines.append(f"- case#{it.case_id}: {snippet[:300]}")
        raw = sanitize(_truncate("\n".join(lines)))
        src = record_source(
            db,
            project_id=project_id,
            source_type="execution",
            source_id=task_id,
            title=f"执行失败摘要 {task.name or task.task_id}",
            source_ref=task.task_id or "",
            raw_content=raw,
            metadata={"failed": len(failed_items), "environment_id": task.environment_id},
        )
        if src is None:
            db.commit()
            return
        chunk_service.make_chunks(db, src, [{
            "chunk_type": "execution_result",
            "title": f"执行失败 {task.name or task.task_id}",
            "content": raw,
            "tags": ["execution", "failed"],
        }])
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
    except Exception:
        logger.exception("ingest execution failure task_id=%s failed", task_id)
        db.rollback()
    finally:
        db.close()


# ── 6. UI 测试失败回流入库 ──

def ingest_ui_test_failure_in_new_session(project_id: int, run_id: int) -> None:
    """UI 自动化执行失败后，提取失败摘要和错误信息沉淀到知识库。"""
    if not settings.knowledge_ingest_enabled:
        return
    db = SessionLocal()
    try:
        from app.models.ui_test import UiTestRun, UiTestJob
        from app.models.environment import Environment

        run = db.get(UiTestRun, run_id)
        if not run:
            return

        if run.status != "fail":
            return  # 只摄入失败记录

        job = db.get(UiTestJob, run.job_id)
        if not job:
            return

        # 生产环境保护
        if job.environment_id:
            env = db.get(Environment, job.environment_id)
            if env and env.env_type == "prod" and not settings.knowledge_ingest_production_data:
                logger.info("skip prod UI test ingest run_id=%s (flag off)", run_id)
                return

        # 构建知识切片内容
        import json as _json
        try:
            result = _json.loads(run.result or "{}")
        except (_json.JSONDecodeError, TypeError):
            result = {}

        raw_lines = [
            f"UI 自动化执行失败 - {job.name}",
            f"脚本: {job.test_spec}",
            f"浏览器: {job.browser}",
            f"错误: {run.error_message}",
            f"结果: 总数={result.get('total',0)} 通过={result.get('pass_',0)} 失败={result.get('fail',0)}",
            f"执行时间: {run.started_at.isoformat() if run.started_at else 'N/A'}",
        ]
        raw = "\n".join(raw_lines)

        src = record_source(
            db,
            project_id=project_id,
            source_type="ui_test_execution",
            source_id=run_id,
            title=f"UI 测试 #{run_id}: {job.name}",
            source_ref=str(run_id),
            raw_content=raw,
            metadata={"browser": job.browser, "test_spec": job.test_spec},
        )
        if src is None:
            db.rollback()
            return
        chunk_service.make_chunks(db, src, [{
            "chunk_type": "ui_test_result",
            "title": f"UI 测试失败 #{run_id}: {job.name}",
            "content": raw,
            "tags": ["ui_test", "failed", job.browser],
        }])
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
    except Exception:
        logger.exception("ingest UI test failure run_id=%s failed", run_id)
        db.rollback()
    finally:
        db.close()


# ── Lanhu version diff sync (batch-26) ──

def ingest_lanhu_version_diff(
    project_id: int,
    doc_id: str,
    version: str,
    diff_json: dict | None,
    source_url: str,
    evidence_job_id: int,
) -> None:
    """Sync lanhu version diff to knowledge center.

    When a new version's evidence pack is captured, compare with previous version
    and ingest the changed pages as new knowledge sources. Mark previous version
    sources as superseded rather than deleting them.
    """
    if not settings.knowledge_ingest_enabled:
        return
    if not diff_json:
        return  # initial version — regular ingest handles this

    db = SessionLocal()
    try:
        pages = diff_json.get("pages", [])
        changed_pages = [p for p in pages if p.get("change_type") in ("new", "modified")]

        if not changed_pages:
            return

        source_id = doc_id or source_url
        title = f"蓝湖版本差异 {diff_json.get('base_version', '?')} → {version}"

        # Build content from changed pages
        content_parts = [
            f"## 版本变更: {diff_json.get('base_version', '?')} → {version}",
            f"",
            f"**摘要**: 新增 {diff_json['summary']['new_pages']} 页, "
            f"修改 {diff_json['summary']['modified_pages']} 页, "
            f"不变 {diff_json['summary']['unchanged_pages']} 页, "
            f"删除 {diff_json['summary']['deleted_pages']} 页",
            f"",
        ]
        for p in changed_pages:
            emoji = {"new": "🆕", "modified": "✏️"}.get(p["change_type"], "")
            page_label = p.get('page_name') or f"第{p.get('page_index', 0) + 1}页"
            content_parts.append(f"### {emoji} {page_label}")
            content_parts.append(f"**类型**: {p['change_type']}")
            if p.get("ocr_diff"):
                content_parts.append(f"**变动**: {p['ocr_diff']}")
            content_parts.append("")

        raw = sanitize(_truncate("\n".join(content_parts)))

        # Record as knowledge source
        src = record_source(
            db,
            project_id=project_id,
            source_type="lanhu_version_diff",
            source_id=evidence_job_id,
            title=title,
            source_ref=source_url,
            raw_content=raw,
            version=version,
            metadata={
                "base_version": diff_json.get("base_version", ""),
                "doc_id": doc_id,
                "evidence_job_id": evidence_job_id,
                "change_summary": diff_json.get("summary", {}),
            },
        )
        if src is None:
            db.commit()
            return

        # Create chunks for changed pages
        chunks = [
            {
                "chunk_type": "lanhu_version_diff",
                "title": f"{version} — {p.get('page_name', f'Page {i}')}",
                "content": (
                    f"页面: {p.get('page_name', '')}\n"
                    f"变更类型: {p.get('change_type', '')}\n"
                    f"变动摘要: {p.get('ocr_diff', '')}"
                ),
            }
            for i, p in enumerate(changed_pages)
        ]
        chunk_service.make_chunks(db, src, chunks)

        # Mark previous version sources as superseded (not deleted)
        prev_sources = list(
            db.execute(
                select(KnowledgeSource).where(
                    KnowledgeSource.project_id == project_id,
                    KnowledgeSource.source_type == "lanhu_version_diff",
                    KnowledgeSource.source_ref == source_url,
                    KnowledgeSource.version != version,
                    KnowledgeSource.status == "active",
                )
            ).scalars().all()
        )
        for ps in prev_sources:
            ps.status = "superseded"

        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)

        logger.info(
            "Ingested lanhu version diff: %s → %s, %d changed pages → source #%d",
            diff_json.get("base_version", "?"), version, len(changed_pages), src.id,
        )

    except Exception:
        logger.exception("ingest lanhu version diff failed for doc_id=%s version=%s", doc_id, version)
        db.rollback()
    finally:
        db.close()


# ── 8. 平台研发知识入库（work-logs, ADR, 问题模式等） ──

def ingest_platform_knowledge_in_new_session(
    project_id: int,
    title: str,
    raw_content: str,
    *,
    para_category: str = "inbox",
    knowledge_domain: str = "platform",
    source_ref: str = "",
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> int | None:
    """入库平台研发知识（work-logs, ADR, 问题模式等）。

    返回创建的 knowledge_source.id，去重时返回 None。
    调用方不依赖返回值，仅用于日志/验证。
    """
    if not settings.knowledge_ingest_enabled:
        return None
    db = SessionLocal()
    try:
        raw = sanitize(_truncate(raw_content))
        src = record_source(
            db,
            project_id=project_id,
            source_type="platform_doc",
            source_id=None,
            title=title,
            source_ref=source_ref,
            raw_content=raw,
            metadata={
                **(metadata or {}),
                "para_category": para_category,
                "knowledge_domain": knowledge_domain,
            },
        )
        if src is None:
            db.commit()
            return None
        # 写入专用列
        src.para_category = para_category
        src.knowledge_domain = knowledge_domain
        src.freshness_score = 1.0

        chunks = [
            {
                "chunk_type": "platform_knowledge",
                "title": f"{title} #{i + 1}",
                "content": part,
                "tags": tags or [],
            }
            for i, part in enumerate(chunk_service.slice_text(raw))
        ]
        chunk_service.make_chunks(db, src, chunks)
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
        return src.id
    except Exception:
        logger.exception("ingest platform knowledge failed: %s", title)
        db.rollback()
        return None
    finally:
        db.close()


# ── 9. 灵感捕获入库 ──

def ingest_capture_in_new_session(
    project_id: int,
    title: str,
    content: str,
    *,
    source_url: str = "",
    tags: list[str] | None = None,
) -> int | None:
    """快速捕获灵感/想法/片段 → inbox，后续可由 AI 自动加工分类。

    返回创建的 knowledge_source.id，去重时返回 None。
    """
    if not settings.knowledge_ingest_enabled:
        return None
    db = SessionLocal()
    try:
        raw = sanitize(_truncate(content))
        full_content = f"# {title}\n\n{raw}"
        if source_url:
            full_content += f"\n\n来源: {source_url}"
        src = record_source(
            db,
            project_id=project_id,
            source_type="capture",
            source_id=None,
            title=title,
            source_ref=source_url,
            raw_content=sanitize(full_content),
            metadata={
                "tags": tags or [],
                "capture_method": "manual",
            },
        )
        if src is None:
            db.commit()
            return None
        src.para_category = "inbox"
        src.knowledge_domain = "platform"
        src.freshness_score = 1.0

        chunks = [
            {
                "chunk_type": "capture",
                "title": title,
                "content": full_content,
                "tags": tags or [],
            }
        ]
        chunk_service.make_chunks(db, src, chunks)
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
        return src.id
    except Exception:
        logger.exception("ingest capture failed: %s", title)
        db.rollback()
        return None
    finally:
        db.close()


# ── 10. Agent 产出自动入库 ──

def ingest_agent_task_completed_in_new_session(
    project_id: int,
    agent_run_id: int,
) -> int | None:
    """Agent 执行成功后，将输出物作为知识源入库。"""
    if not settings.knowledge_ingest_enabled:
        return None
    db = SessionLocal()
    try:
        from app.models.knowledge import AgentRun, AiArtifact
        from app.services.knowledge.agent_prompts import AGENT_META

        run = db.get(AgentRun, agent_run_id)
        if not run or run.status != "success":
            return None
        artifact = db.scalar(
            select(AiArtifact).where(AiArtifact.agent_run_id == agent_run_id)
        )
        if not artifact:
            return None

        meta = AGENT_META.get(run.agent_type, {})
        raw = sanitize(_truncate(artifact.content_json or ""))
        src = record_source(
            db,
            project_id=project_id,
            source_type=f"agent_{run.agent_type}",
            source_id=artifact.id,
            title=f"Agent产出: {meta.get('label', run.agent_type)} #{run.id}",
            raw_content=raw,
            metadata={
                "agent_run_id": agent_run_id,
                "agent_type": run.agent_type,
                "confidence": artifact.confidence,
                "para_category": "resource",
                "knowledge_domain": "platform",
            },
        )
        if src is None:
            db.commit()
            return None
        src.para_category = "resource"
        src.knowledge_domain = "platform"
        chunks = [
            {
                "chunk_type": f"agent_output_{run.agent_type}",
                "title": f"{meta.get('label', '')} #{run.id}",
                "content": raw,
                "tags": [run.agent_type, "agent_output"],
            }
        ]
        chunk_service.make_chunks(db, src, chunks)
        db.commit()
        _post_ingest_hooks(project_id, source_id=src.id)
        return src.id
    except Exception:
        logger.exception("ingest agent task completed run_id=%s failed", agent_run_id)
        db.rollback()
        return None
    finally:
        db.close()
