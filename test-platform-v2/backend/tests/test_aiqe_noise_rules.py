"""M4 / TA-027.3：Noise Rules 单测。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.aiqe.models.noise_rule import NoiseRule
from app.aiqe.services.noise_rule_service import (
    NoiseRuleError,
    create_rule,
    delete_rule,
    is_effective,
    list_rules,
    renew_rule,
    update_rule,
)


def rule(db_session, **kwargs):
    # AUD-019：suppress 规则必须说明 reason，且默认需要人工批准后生效。
    payload = {
        "project_id": 1,
        "pattern": "广告抖动",
        "action": "suppress",
        "reason": "已知广告抖动非产品缺陷",
        "require_approval": False,
    }
    payload.update(kwargs)
    return create_rule(db_session, **payload)


def test_default_expiry_is_90_days(db_session):
    row = rule(db_session)
    delta = row.expires_at - row.created_at
    assert timedelta(days=89, hours=23) < delta <= timedelta(days=90, minutes=1)
    assert is_effective(row) is True


def test_permanent_quarantine_rejected(db_session):
    with pytest.raises(NoiseRuleError):
        rule(db_session, action="quarantine")


def test_expiry_over_90_days_rejected(db_session):
    with pytest.raises(NoiseRuleError):
        rule(db_session, expires_at=datetime.now(UTC) + timedelta(days=91))


def test_expired_rule_not_effective(db_session):
    row = rule(db_session)
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    assert is_effective(row) is False
    assert list_rules(db_session, 1, include_expired=False) == []


def test_renew_extends_90_days(db_session):
    row = rule(db_session)
    old = row.expires_at
    renewed = renew_rule(db_session, row.id, require_approval=False)
    assert renewed.expires_at > old
    assert renewed.status == "active"
    assert is_effective(renewed) is True
    # AUD-019：续期新建版本，旧版本标记 superseded
    assert renewed.version == 2
    assert renewed.supersedes_id == row.id
    assert row.status == "superseded"


def test_update_pattern_and_action(db_session):
    row = rule(db_session)
    updated = update_rule(db_session, row.id, pattern="新规则", action="hint")
    assert updated.pattern == "新规则" and updated.action == "hint"


def test_delete_rule(db_session):
    row = rule(db_session)
    delete_rule(db_session, row.id)
    assert db_session.query(NoiseRule).count() == 0


def test_invalid_action_and_empty_pattern(db_session):
    with pytest.raises(NoiseRuleError):
        rule(db_session, action="ignore")
    with pytest.raises(NoiseRuleError):
        rule(db_session, pattern=" ")
