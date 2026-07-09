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
from app.services.knowledge import chunk_service
from app.services.knowledge.sanitize import sanitize
from app.services.knowledge.source_service import record_source

logger = logging.getLogger("knowledge.ingest")

_MAX_RAW = 20000  # 单条 raw_content 上限，避免超大文档撑爆


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
    except Exception:
        logger.exception("ingest execution failure task_id=%s failed", task_id)
        db.rollback()
    finally:
        db.close()
