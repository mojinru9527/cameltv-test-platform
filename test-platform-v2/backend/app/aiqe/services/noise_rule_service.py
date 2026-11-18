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
    environment_id: int | None = None,
    profile_id: str | None = None,
    detector_key: str | None = None,
    error_class: str | None = None,
    selector: dict | None = None,
    app_version: str | None = None,
    evidence_refs: list | None = None,
    reason: str = "",
    require_approval: bool = True,
) -> NoiseRule:
    if not str(pattern or "").strip():
        raise NoiseRuleError("规则 pattern 不能为空")
    if action not in ACTIONS:
        raise NoiseRuleError(f"未知 action: {action!r}")
    if action == "suppress" and not str(reason or "").strip():
        raise NoiseRuleError("suppress 规则必须填写 reason（治理要求）")
    now = _utcnow()
    expiry = _resolve_expiry(expires_at, action=action, base=now, now=now)
    row = NoiseRule(
        project_id=project_id,
        pattern=str(pattern).strip(),
        action=action,
        scope=scope,
        environment_id=environment_id,
        profile_id=profile_id,
        detector_key=detector_key,
        error_class=error_class,
        selector_json=selector,
        app_version=app_version,
        evidence_refs_json=list(evidence_refs or []),
        reason=str(reason or ""),
        version=1,
        valid_from=now,
        expires_at=expiry,
        status="pending_approval" if require_approval else "active",
        approved_by=None if require_approval else created_by,
        approved_at=None if require_approval else now,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def get_rule(db: Session, rule_id: int, *, project_id: int | None = None) -> NoiseRule:
    row = db.get(NoiseRule, rule_id)
    if row is None or (
        project_id is not None and int(row.project_id or 0) != int(project_id)
    ):
        raise NoiseRuleError(f"规则不存在: {rule_id}")
    return row


def approve_rule(
    db: Session, rule_id: int, *, project_id: int, approved_by: int
) -> NoiseRule:
    """AUD-019：规则必须经人工批准才能生效（禁止创建即 active）。"""
    row = get_rule(db, rule_id, project_id=project_id)
    if row.status == "active":
        return row
    row.status = "active"
    row.approved_by = int(approved_by)
    row.approved_at = _utcnow()
    row.updated_at = _utcnow()
    db.flush()
    return row


def assert_not_p0(rule: NoiseRule, *, priority: str | None) -> None:
    """P0 原始 FAIL 永远不能通过 suppress/quarantine 转成 PASS。"""
    if str(priority or "").upper() == "P0" and rule.action in {"suppress", "quarantine"}:
        raise NoiseRuleError("P0 结果不允许被 Noise Rule 抑制/隔离")


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


def renew_rule(
    db: Session,
    rule_id: int,
    *,
    project_id: int | None = None,
    approved_by: int | None = None,
    require_approval: bool = True,
) -> NoiseRule:
    """AUD-019：续期**新建版本**（旧行保留只读），并强制重新审批。"""
    previous = get_rule(db, rule_id, project_id=project_id)
    now = _utcnow()
    row = NoiseRule(
        project_id=int(previous.project_id),
        pattern=previous.pattern,
        action=previous.action,
        scope=previous.scope,
        environment_id=previous.environment_id,
        profile_id=previous.profile_id,
        detector_key=previous.detector_key,
        error_class=previous.error_class,
        selector_json=previous.selector_json,
        app_version=previous.app_version,
        evidence_refs_json=previous.evidence_refs_json,
        reason=previous.reason,
        version=int(previous.version or 1) + 1,
        valid_from=now,
        expires_at=_resolve_expiry(None, action=previous.action, base=now, now=now),
        supersedes_id=int(previous.id),
        status="active" if not require_approval else "pending_approval",
        approved_by=approved_by if not require_approval else None,
        approved_at=now if not require_approval else None,
        created_by=int(previous.created_by or 0),
        created_at=now,
        updated_at=now,
    )
    previous.status = "superseded"
    previous.updated_at = now
    db.add(row)
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


def delete_rule(db: Session, rule_id: int, *, project_id: int | None = None) -> None:
    row = get_rule(db, rule_id, project_id=project_id)
    db.delete(row)
    db.flush()


def record_match(
    db: Session, rule_id: int, *, suppressed: bool = True, false_suppress: bool = False
) -> NoiseRule:
    row = get_rule(db, rule_id)
    if suppressed:
        row.matched_count = int(row.matched_count or 0) + 1
    if false_suppress:
        row.false_suppress_count = int(row.false_suppress_count or 0) + 1
    row.updated_at = _utcnow()
    db.flush()
    return row
