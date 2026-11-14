"""M5 / TA-030：A6 Learning Curator（候选规则 → benchmark → 人审 → ACTIVE）。

护栏：
- 未 benchmark 不得批准；
- 误报率 > 20% 不得批准；
- 重复候选必须人工确认（acknowledged），且激活时合并到已有 pattern，不新增重复规则。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.learning import BugPattern, LearningCandidate

FALSE_POSITIVE_LIMIT = 0.2
STATUSES = ("draft", "benchmarked", "approved", "active", "rejected")


class LearningError(ValueError):
    pass


def create_candidate(
    db: Session,
    *,
    project_id: int,
    rule: dict[str, Any],
    source: str = "bug",
    duplicate_of: str | None = None,
) -> LearningCandidate:
    if not isinstance(rule, dict) or not str(rule.get("pattern") or "").strip():
        raise LearningError("候选规则必须包含非空 pattern")
    row = LearningCandidate(
        project_id=project_id,
        rule_json=rule,
        source=source,
        duplicate_of=duplicate_of,
        status="draft",
    )
    db.add(row)
    db.flush()
    return row


def get_candidate(
    db: Session, candidate_id: str, *, project_id: int | None = None
) -> LearningCandidate:
    row = db.get(LearningCandidate, candidate_id)
    if row is None or (
        project_id is not None and int(row.project_id or 0) != int(project_id)
    ):
        raise LearningError(f"候选不存在: {candidate_id}")
    return row


def evaluate_candidate(
    db: Session,
    candidate_id: str,
    benchmark: dict[str, Any],
    *,
    project_id: int | None = None,
) -> LearningCandidate:
    row = get_candidate(db, candidate_id, project_id=project_id)
    rate = benchmark.get("false_positive_rate")
    samples = benchmark.get("sample_size")
    if not isinstance(rate, (int, float)) or not 0 <= float(rate) <= 1:
        raise LearningError("benchmark 必须包含 0..1 的 false_positive_rate")
    if not isinstance(samples, int) or samples <= 0:
        raise LearningError("benchmark 必须包含正向 sample_size")
    row.benchmark_json = dict(benchmark)
    row.status = "benchmarked"
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def approve_candidate(
    db: Session,
    candidate_id: str,
    *,
    acknowledge_duplicate: bool = False,
    project_id: int | None = None,
) -> LearningCandidate:
    row = get_candidate(db, candidate_id, project_id=project_id)
    if row.status not in ("benchmarked",):
        raise LearningError("必须先完成 benchmark 才能批准")
    rate = float((row.benchmark_json or {}).get("false_positive_rate", 1))
    if rate > FALSE_POSITIVE_LIMIT:
        raise LearningError(f"误报率过高（{rate:.0%} > 20%），不得发布")
    if row.duplicate_of and not (acknowledge_duplicate or row.acknowledged):
        raise LearningError("重复候选需人工确认（acknowledge_duplicate）")
    row.acknowledged = True
    row.status = "approved"
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def activate_candidate(
    db: Session, candidate_id: str, *, project_id: int | None = None
) -> BugPattern | None:
    row = get_candidate(db, candidate_id, project_id=project_id)
    if row.status != "approved":
        raise LearningError("只有 approved 候选才能 ACTIVE")
    if row.duplicate_of:
        row.status = "active"
        row.updated_at = datetime.now(UTC)
        db.flush()
        return None
    key = str(row.rule_json["pattern"]).strip()
    existing = db.scalar(select(BugPattern).where(BugPattern.pattern_key == key))
    if existing is not None:
        # 未显式标记 duplicate 但 key 已存在：合并，不新增重复规则
        row.duplicate_of = existing.id
        row.status = "active"
        row.updated_at = datetime.now(UTC)
        db.flush()
        return existing
    pattern = BugPattern(
        pattern_key=key,
        description=str(row.rule_json.get("description") or ""),
        status="active",
        source_candidate_id=row.id,
    )
    db.add(pattern)
    row.status = "active"
    row.updated_at = datetime.now(UTC)
    db.flush()
    return pattern


def list_candidates(db: Session, project_id: int) -> list[LearningCandidate]:
    return list(
        db.scalars(
            select(LearningCandidate)
            .where(LearningCandidate.project_id == project_id)
            .order_by(LearningCandidate.created_at.desc())
        )
    )

def list_bug_patterns(
    db: Session, *, status: str | None = "active", limit: int = 100
) -> list[BugPattern]:
    """batch-349：BugPattern 只读查询（Console 学习页）。"""
    stmt = select(BugPattern).order_by(BugPattern.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(BugPattern.status == status)
    return list(db.scalars(stmt))
