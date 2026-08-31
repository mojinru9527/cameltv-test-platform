"""AITDE V4.0 (V40-003) VersionMission write-cutoff policy tests."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.exceptions import APIException
from app.modules.aitde.legacy_cutover.service import CompatibilityPolicy


def test_policy_allows_write_in_active_stage(monkeypatch):
    monkeypatch.setattr(settings, "version_mission_write_stage", "ACTIVE")
    # ACTIVE must not raise; reads are never gated.
    CompatibilityPolicy.enforce_v1_write("version-mission")


def test_policy_blocks_write_in_readonly_stage(monkeypatch):
    monkeypatch.setattr(settings, "version_mission_write_stage", "READONLY")
    with pytest.raises(APIException) as exc:
        CompatibilityPolicy.enforce_v1_write("version-mission")
    assert exc.value.http_status == 410
    assert "cut off" in str(exc.value.msg)


def test_policy_stage_reads_setting(monkeypatch):
    monkeypatch.setattr(settings, "version_mission_write_stage", "readonly")
    assert CompatibilityPolicy.v1_write_stage() == "READONLY"
    monkeypatch.setattr(settings, "version_mission_write_stage", "ACTIVE")
    assert CompatibilityPolicy.v1_write_stage() == "ACTIVE"


def test_policy_missing_setting_defaults_active(monkeypatch):
    monkeypatch.delattr(settings, "version_mission_write_stage", raising=False)
    # Lazy read in the policy tolerates a missing setting defaulting to ACTIVE.
    assert CompatibilityPolicy.v1_write_stage() == "ACTIVE"
    CompatibilityPolicy.enforce_v1_write("version-mission")
