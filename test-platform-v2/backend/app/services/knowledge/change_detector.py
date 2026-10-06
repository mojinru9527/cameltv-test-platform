"""变更检测服务（M5）—— 内容哈希对比 + 可配置触发规则。

核心能力：
- 检测知识源的 content_hash 变更
- 按规则匹配事件类型 → 触发 Agent 类型
- 防抖：同一 (项目, 源, Agent) 5 分钟内不重复触发；防抖状态**持久化在数据库**，
  进程重启不能绕过（P1-9）
- 自喂环断路器：Agent 运行期间的嵌套入库/变更检测不再触发新 Agent（P1-9）
"""
from __future__ import annotations

import hashlib
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeSource, KnowledgeTriggerDebounce
from app.services.knowledge.agent_orchestrator import run_agent_in_new_session

logger = logging.getLogger("knowledge.change_detector")

# 防抖窗口（秒）
_DEBOUNCE_SECONDS = 300


@dataclass
class ChangeEvent:
    source_id: int
    source_type: str
    event_type: str  # requirement_updated / api_schema_changed / new_defect / execution_failure
    title: str
    project_id: int
    old_hash: str = ""
    new_hash: str = ""


# ── 触发规则配置（默认） ──

TRIGGER_RULES: dict[str, list[str]] = {
    "requirement_updated": ["requirement_analysis", "impact_analysis"],
    "api_schema_changed": ["impact_analysis", "case_generation"],
    "new_defect": ["failure_analysis"],
    "execution_failure": ["failure_analysis"],
}


def _compute_content_hash(content: str) -> str:
    """计算内容哈希（SHA256 前 16 字符）。"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ── 变更检测 ──

def detect_changes(project_id: int) -> list[ChangeEvent]:
    """扫描项目内所有 active 知识源，对比内容哈希检测变更。返回变更事件列表。"""
    db = SessionLocal()
    events: list[ChangeEvent] = []
    try:
        sources = list(
            db.scalars(
                select(KnowledgeSource).where(
                    KnowledgeSource.project_id == project_id,
                    KnowledgeSource.is_deleted.is_(False),
                )
            ).all()
        )
        for src in sources:
            raw = src.raw_content or ""
            new_hash = _compute_content_hash(raw)
            metadata = {}
            try:
                import json
                metadata = json.loads(src.metadata_json or "{}")
            except (json.JSONDecodeError, TypeError):
                logger.warning("源 metadata_json 解析失败，按空处理: %s", getattr(src, "id", "?"))

            old_hash = metadata.get("content_hash", "")
            if new_hash != old_hash and old_hash:
                # 有实际变更
                event_type = _source_type_to_event(src.source_type)
                events.append(ChangeEvent(
                    source_id=src.id,
                    source_type=src.source_type,
                    event_type=event_type,
                    title=src.title or f"Source#{src.id}",
                    project_id=project_id,
                    old_hash=old_hash,
                    new_hash=new_hash,
                ))

            # 更新哈希（无论是否变更）
            metadata["content_hash"] = new_hash
            src.metadata_json = json.dumps(metadata, ensure_ascii=False)

        db.commit()
    except Exception:
        logger.exception("Change detection failed for project %s", project_id)
        db.rollback()
    finally:
        db.close()

    return events


def _source_type_to_event(source_type: str) -> str:
    """知识源类型 → 变更事件类型。"""
    mapping = {
        "requirement": "requirement_updated",
        "openapi": "api_schema_changed",
        "defect": "new_defect",
        "execution": "execution_failure",
        "test_case": "api_schema_changed",
    }
    return mapping.get(source_type, "api_schema_changed")


# ── 自动触发调度 ──

# P1-9 自喂环断路器。
# 链路：入库 → 变更检测 → 触发 Agent（出网 LLM）→ Agent 产出物再入库 → 变更检测 → …
# 若不在「已经在自动触发链路里」时断开，一次 UI 执行失败就能自我放大成无限 LLM 调用。
# 用 ContextVar（而非模块全局变量）保证请求线程 / 定时线程 / 协程之间互不串味。
_AGENT_TRIGGER_DEPTH: ContextVar[int] = ContextVar("knowledge_agent_trigger_depth", default=0)


@contextmanager
def agent_trigger_scope() -> Iterator[None]:
    """标记「当前调用栈已处于自动 Agent 触发链路中」。"""
    token = _AGENT_TRIGGER_DEPTH.set(_AGENT_TRIGGER_DEPTH.get() + 1)
    try:
        yield
    finally:
        _AGENT_TRIGGER_DEPTH.reset(token)


def in_agent_trigger_scope() -> bool:
    """当前是否处于自动 Agent 触发链路内（用于阻断自喂环）。"""
    return _AGENT_TRIGGER_DEPTH.get() > 0


def _debounce_key(project_id: int, source_id: int, agent_type: str) -> str:
    return f"{project_id}:{source_id}:{agent_type}"


def _debounce_blocks(
    project_id: int,
    source_id: int,
    agent_type: str,
    *,
    db: Session | None = None,
) -> bool:
    """持久化防抖：窗口内已触发过则返回 True（并且不刷新时间戳）。

    选型说明：用 DB 行而不是存储目录下的文件——防抖状态天然是「(项目, 源, Agent)
    三元组的唯一时间戳」，DB 唯一约束能直接表达，也跟随本仓库已有的
    SQLite/PG 双栈与迁移体系（对比 `ai_gateway_cache`）；文件方案还要自己处理
    并发写与清理。查询/写入异常一律**失败关闭**（返回 True 不触发）：
    宁可漏触发一次，也不能因为防抖状态读不出来就重复烧钱。
    """
    own_session = db is None
    session = db
    key = _debounce_key(project_id, source_id, agent_type)
    try:
        if session is None:
            session = SessionLocal()
        row = session.scalar(
            select(KnowledgeTriggerDebounce).where(
                KnowledgeTriggerDebounce.project_id == project_id,
                KnowledgeTriggerDebounce.source_id == source_id,
                KnowledgeTriggerDebounce.agent_type == agent_type,
            )
        )
        now = datetime.now()
        if row is not None and row.triggered_at is not None:
            if row.triggered_at > now - timedelta(seconds=_DEBOUNCE_SECONDS):
                logger.debug("Debounced: %s (last=%s)", key, row.triggered_at)
                return True
            row.triggered_at = now
        else:
            session.add(
                KnowledgeTriggerDebounce(
                    project_id=project_id,
                    source_id=source_id,
                    agent_type=agent_type,
                    triggered_at=now,
                )
            )
        session.commit()
        return False
    except Exception:
        logger.exception("防抖状态读写失败，按失败关闭跳过本次自动触发: %s", key)
        if session is not None:
            try:
                session.rollback()
            except Exception:
                logger.warning("防抖状态回滚失败（已忽略）: %s", key, exc_info=True)
        return True
    finally:
        if own_session and session is not None:
            session.close()


def handle_changes(project_id: int, auto_trigger: bool = False) -> dict[str, int]:
    """检测变更并按规则触发 Agent。

    Args:
        project_id: 项目 ID
        auto_trigger: 是否自动触发 Agent（需要手动开启）

    Returns:
        {"detected": N, "triggered": N}
    """
    events = detect_changes(project_id)
    triggered = 0

    if not auto_trigger or not events:
        return {"detected": len(events), "triggered": 0}

    # P1-9：Agent 运行期间产生的入库不许再触发 Agent（自喂环断路）
    if in_agent_trigger_scope():
        logger.info(
            "检测到 %s 个变更，但当前处于自动 Agent 触发链路内，跳过触发以防自喂环",
            len(events),
        )
        return {"detected": len(events), "triggered": 0}

    for event in events:
        agent_types = TRIGGER_RULES.get(event.event_type, [])
        for agent_type in agent_types:
            if _debounce_blocks(project_id, event.source_id, agent_type):
                continue

            # 先登记防抖再触发：Agent 自己失败也不能立刻进入重试风暴
            with agent_trigger_scope():
                run_agent_in_new_session(
                    project_id=project_id,
                    agent_type=agent_type,
                    user_input=f"检测到变更: {event.title} ({event.event_type})",
                    params={"source_id": event.source_id, "event_type": event.event_type},
                )
            triggered += 1
            logger.info("Auto-triggered %s for source#%s (event=%s)", agent_type, event.source_id, event.event_type)

    return {"detected": len(events), "triggered": triggered}


# ── API 触发端点 ──

def check_changes_manual(project_id: int) -> dict[str, Any]:
    """手动触发变更检测（不自动运行 Agent），返回检测到的变更列表。"""
    events = detect_changes(project_id)
    return {
        "detected": len(events),
        "changes": [
            {
                "source_id": e.source_id,
                "source_type": e.source_type,
                "event_type": e.event_type,
                "title": e.title,
            }
            for e in events
        ],
    }
