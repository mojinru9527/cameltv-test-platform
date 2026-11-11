"""M4 / TA-027.3：Noise Suppression Rules（90 天强制复核、禁止永久 quarantine）。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.noise_rule import NoiseRule

ACTIONS = frozenset({"suppress", "hint", "quarantine"})
MAX_DAYS = 90


class NoiseRuleError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _resolve_expiry(
    expires_at: datetime | None, *, action: str, base: datetime, now: datetime
) -> datetime:
    if expires_at is None:
        if action == "quarantine":
            raise NoiseRuleError("quarantine 必须有到期时间，禁止永久隔离")
        return base + timedelta(days=MAX_DAYS)
    expiry = _as_aware(expires_at)
    if expiry <= now:
        raise NoiseRuleError("到期时间必须晚于当前时间")
    if expiry > base + timedelta(days=MAX_DAYS):
        raise NoiseRuleError("规则有效期不得超过 90 天（强制复核）")
    return expiry


def create_rule(
    db: Session,
    *,
    project_id: int,
    pattern: str,
    action: str = "suppress",
    scope: str = "run",
    expires_at: datetime | None = None,
    created_by: int = 0,
) -> NoiseRule:
    if not str(pattern or "").strip():
        raise NoiseRuleError("规则 pattern 不能为空")
    if action not in ACTIONS:
        raise NoiseRuleError(f"未知 action: {action!r}")
    now = _utcnow()
    expiry = _resolve_expiry(expires_at, action=action, base=now, now=now)
    row = NoiseRule(
        project_id=project_id,
        pattern=str(pattern).strip(),
        action=action,
        scope=scope,
        expires_at=expiry,
        status="active",
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def get_rule(db: Session, rule_id: int) -> NoiseRule:
    row = db.get(NoiseRule, rule_id)
    if row is None:
        raise NoiseRuleError(f"规则不存在: {rule_id}")
    return row


def update_rule(
    db: Session,
    rule_id: int,
    *,
    pattern: str | None = None,
    action: str | None = None,
    expires_at: datetime | None = None,
) -> NoiseRule:
    row = get_rule(db, rule_id)
    now = _utcnow()
    next_action = action or row.action
    if next_action not in ACTIONS:
        raise NoiseRuleError(f"未知 action: {next_action!r}")
    base = _as_aware(row.created_at) if row.created_at else now
    if expires_at is not None:
        row.expires_at = _resolve_expiry(expires_at, action=next_action, base=base, now=now)
    elif next_action == "quarantine" and row.action != "quarantine":
        raise NoiseRuleError("quarantine 必须有到期时间，禁止永久隔离")
    if pattern is not None:
        if not pattern.strip():
            raise NoiseRuleError("规则 pattern 不能为空")
        row.pattern = pattern.strip()
    row.action = next_action
    row.status = "active"
    row.updated_at = now
    db.flush()
    return row


def renew_rule(db: Session, rule_id: int) -> NoiseRule:
    row = get_rule(db, rule_id)
    now = _utcnow()
    row.expires_at = now + timedelta(days=MAX_DAYS)
    row.status = "active"
    row.updated_at = now
    db.flush()
    return row


def is_effective(rule: NoiseRule, *, now: datetime | None = None) -> bool:
    current = now or _utcnow()
    return rule.status == "active" and _as_aware(rule.expires_at) > current


def list_rules(db: Session, project_id: int, *, include_expired: bool = True) -> list[NoiseRule]:
    rows = list(
        db.scalars(
            select(NoiseRule)
            .where(NoiseRule.project_id == project_id)
            .order_by(NoiseRule.created_at.desc())
        )
    )
    if include_expired:
        return rows
    return [row for row in rows if is_effective(row)]


def delete_rule(db: Session, rule_id: int) -> None:
    row = get_rule(db, rule_id)
    db.delete(row)
    db.flush()
