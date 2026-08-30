"""知识库差异对比编排 —— 抽取左右契约 → 分类 → 落 WikiDiffTask/Item；差异转待审产物。

run_diff_in_new_session 自带 Session（BackgroundTasks 调度）。create_artifact_from_item
在请求 Session 内把差异项转为 pending AiArtifact，复用现有 AI 审核台。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.knowledge import AiArtifact
from app.models.wiki import WikiDiffItem, WikiDiffTask
from app.services.knowledge.artifact_confidence import severity_confidence
from app.services.wiki import contract_extractor, diff_classifier

logger = logging.getLogger("wiki.compare")

# 差异维度 → AI 产物类型（AiArtifact.artifact_type 复用既有枚举）
_DIMENSION_ARTIFACT = {
    "业务规则": "business_rule",
    "版本": "regression_scope",
    "字段": "test_case",
    "接口": "test_case",
    "异常路径": "test_case",
    "权限角色": "business_rule",
    "数据依赖": "test_data",
    "验收标准": "test_case",
    "测试覆盖": "test_case",
    "客户端": "regression_scope",
    "需求范围": "impact_analysis",
    "证据": "impact_analysis",
}


def _artifact_type_for(dimension: str) -> str:
    return _DIMENSION_ARTIFACT.get(dimension, "test_case")


def run_diff_in_new_session(project_id: int, task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(WikiDiffTask, task_id)
        if not task or task.project_id != project_id or task.status == "success":
            return
        task.status = "running"
        db.commit()

        left_ref = json.loads(task.left_ref_json or "{}")
        right_ref = json.loads(task.right_ref_json or "{}")
        left = contract_extractor.extract_contract(
            db, project_id, kb_type=left_ref.get("kb_type", "platform_rag"),
            query=left_ref.get("query", ""))
        right = contract_extractor.extract_contract(
            db, project_id, kb_type=right_ref.get("kb_type", "platform_wiki"),
            query=right_ref.get("query", ""))

        items = diff_classifier.classify(left, right)
        for it in items:
            db.add(WikiDiffItem(
                task_id=task.id, project_id=project_id,
                dimension=it["dimension"], diff_type=it["diff_type"], severity=it["severity"],
                title=it["title"], left_value=it["left_value"], right_value=it["right_value"],
                evidence_json=json.dumps(it["evidence"], ensure_ascii=False),
                suggestion=it["suggestion"],
            ))

        summary = diff_classifier.summarize(items)
        summary["left_contract"] = left
        summary["right_contract"] = right
        task.summary_json = json.dumps(summary, ensure_ascii=False)
        task.status = "success"
        task.finished_at = datetime.now()
        db.commit()
    except Exception as e:
        logger.exception("diff task failed: task=%s", task_id)
        db.rollback()
        try:
            task = db.get(WikiDiffTask, task_id)
            if task:
                task.status = "failed"
                task.error_message = str(e)[:500]
                task.finished_at = datetime.now()
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def create_artifact_from_item(
    db: Session, project_id: int, item: WikiDiffItem, *, artifact_type: str = "", operator_id: int = 0,
) -> AiArtifact:
    """把差异项转为 pending AiArtifact，并回写 item.resolved_artifact_id + 标记 accepted。"""
    atype = artifact_type or _artifact_type_for(item.dimension)
    content = {
        "from_diff_item": item.id,
        "dimension": item.dimension,
        "diff_type": item.diff_type,
        "severity": item.severity,
        "title": item.title,
        "left_value": item.left_value,
        "right_value": item.right_value,
        "suggestion": item.suggestion,
    }
    art = AiArtifact(
        project_id=project_id, artifact_type=atype,
        title=f"[差异补齐] {item.title}"[:200],
        content_json=json.dumps(content, ensure_ascii=False),
        source_refs=item.evidence_json or "[]",
        review_status="pending", confidence=severity_confidence(item.severity),
    )
    db.add(art)
    db.flush()
    item.resolved_artifact_id = art.id
    item.review_status = "accepted"
    db.flush()
    return art


# ── 路由层 ORM 收敛薄函数（Batch 181 路由拆分）──

def create_diff_task(
    db: Session,
    *,
    project_id: int,
    title: str,
    compare_type: str,
    left_ref_json: str,
    right_ref_json: str,
    created_by: int = 0,
) -> WikiDiffTask:
    """创建 pending 差异任务并 flush（沿用调用方会话，提交由路由层负责）。"""
    task = WikiDiffTask(
        project_id=project_id, title=title,
        compare_type=compare_type, status="pending",
        left_ref_json=left_ref_json,
        right_ref_json=right_ref_json,
        created_by=created_by,
    )
    db.add(task)
    db.flush()
    return task


def list_diff_tasks(
    db: Session,
    project_id: int,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WikiDiffTask], int]:
    """分页列出项目差异任务（按 id 倒序）。"""
    q = db.query(WikiDiffTask).filter(WikiDiffTask.project_id == project_id)
    if status:
        q = q.filter(WikiDiffTask.status == status)
    total = q.count()
    rows = q.order_by(WikiDiffTask.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def get_diff_task(db: Session, task_id: int, project_id: int) -> WikiDiffTask | None:
    """项目作用域内获取差异任务。"""
    task = db.get(WikiDiffTask, task_id)
    if not task or task.project_id != project_id:
        return None
    return task


def list_diff_items(
    db: Session,
    task_id: int,
    *,
    dimension: str | None = None,
    diff_type: str | None = None,
    severity: str | None = None,
    review_status: str | None = None,
) -> list[WikiDiffItem]:
    """按过滤条件列出差异项（按 severity/id 排序，与路由原逻辑一致）。"""
    q = db.query(WikiDiffItem).filter(WikiDiffItem.task_id == task_id)
    if dimension:
        q = q.filter(WikiDiffItem.dimension == dimension)
    if diff_type:
        q = q.filter(WikiDiffItem.diff_type == diff_type)
    if severity:
        q = q.filter(WikiDiffItem.severity == severity)
    if review_status:
        q = q.filter(WikiDiffItem.review_status == review_status)
    return q.order_by(WikiDiffItem.severity, WikiDiffItem.id).all()


def get_diff_item(db: Session, item_id: int, project_id: int) -> WikiDiffItem | None:
    """项目作用域内获取差异项。"""
    item = db.get(WikiDiffItem, item_id)
    if not item or item.project_id != project_id:
        return None
    return item
