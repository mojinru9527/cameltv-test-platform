"""变更检测服务（M5）—— 内容哈希对比 + 可配置触发规则。

核心能力：
- 检测知识源的 content_hash 变更
- 按规则匹配事件类型 → 触发 Agent 类型
- 防抖：同一 source 5 分钟内不重复触发
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.knowledge import KnowledgeSource
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
                    KnowledgeSource.status.notin_(("deprecated", "superseded")),
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
                pass

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

_last_trigger: dict[str, float] = {}  # key: "project_id:source_id:agent_type" → timestamp


def _debounce_key(project_id: int, source_id: int, agent_type: str) -> str:
    return f"{project_id}:{source_id}:{agent_type}"


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

    now = time.time()
    for event in events:
        agent_types = TRIGGER_RULES.get(event.event_type, [])
        for agent_type in agent_types:
            key = _debounce_key(project_id, event.source_id, agent_type)
            last = _last_trigger.get(key, 0)
            if now - last < _DEBOUNCE_SECONDS:
                logger.debug("Debounced: %s (last=%.0fs ago)", key, now - last)
                continue

            _last_trigger[key] = now
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
