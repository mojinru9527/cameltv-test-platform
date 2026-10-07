"""存储保留期清理测试（保留面）。

平台简化批次：DSH 任务体系删除后，原测试文件的 dsh-sessions 分支已随之移除；
此处覆盖仍然生效的行为——ui-runs 数字目录按 mtime 清理、plan-sync 默认不清理、
显式根目录优先、默认根与 playwright_executor 同源。
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import storage_retention


def _make_dir(path: Path, *, age_days: float, size_bytes: int = 1024) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    payload = path / "artifact.bin"
    payload.write_bytes(b"x" * size_bytes)
    stamp = time.time() - age_days * 86400
    os.utime(payload, (stamp, stamp))
    os.utime(path, (stamp, stamp))
    return path


@pytest.fixture()
def retention_root(tmp_path, monkeypatch):
    root = tmp_path / "storage"
    (root / "ui-runs").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "storage_retention_root", str(root), raising=False)
    monkeypatch.setattr(settings, "storage_retention_days", 7, raising=False)
    monkeypatch.setattr(settings, "storage_retention_enabled", True, raising=False)
    monkeypatch.setattr(settings, "storage_retention_include_plan_sync", False, raising=False)
    return root


def test_default_root_shares_playwright_executor_convention(monkeypatch):
    """未配置根目录时，必须落在 backend/storage（容器内 /app/storage）。"""
    monkeypatch.setattr(settings, "storage_retention_root", "", raising=False)
    from app.services.playwright_executor import STORAGE_DIR

    assert storage_retention._storage_root() == STORAGE_DIR.parent


def test_expired_numeric_run_dirs_are_removed_and_fresh_kept(retention_root):
    old = _make_dir(retention_root / "ui-runs" / "101", age_days=10)
    fresh = _make_dir(retention_root / "ui-runs" / "102", age_days=1)

    stats = storage_retention.cleanup_storage()

    assert stats["ui_runs_deleted"] == 1
    assert not old.exists()
    assert fresh.exists()
    assert stats["root"] == str(retention_root)


def test_non_numeric_dirs_are_never_touched(retention_root):
    """plan-sync 等非数字目录默认不清理（与历史计划记录关联）。"""
    plan_sync = _make_dir(retention_root / "ui-runs" / "plan-sync" / "run-1", age_days=30)
    notes = retention_root / "ui-runs" / "keep-me"
    _make_dir(notes, age_days=30)

    stats = storage_retention.cleanup_storage()

    assert stats["ui_runs_deleted"] == 0
    assert stats["plan_sync_deleted"] == 0
    assert plan_sync.exists()
    assert notes.exists()


def test_plan_sync_cleanup_requires_explicit_opt_in(retention_root, monkeypatch):
    stale = _make_dir(retention_root / "ui-runs" / "plan-sync" / "run-old", age_days=30)
    fresh = _make_dir(retention_root / "ui-runs" / "plan-sync" / "run-new", age_days=1)
    monkeypatch.setattr(settings, "storage_retention_include_plan_sync", True, raising=False)

    stats = storage_retention.cleanup_storage()

    assert stats["plan_sync_deleted"] == 1
    assert not stale.exists()
    assert fresh.exists()


def test_explicit_root_wins_over_default(tmp_path, monkeypatch):
    explicit = tmp_path / "custom-root"
    (explicit / "ui-runs").mkdir(parents=True, exist_ok=True)
    _make_dir(explicit / "ui-runs" / "7", age_days=30)
    monkeypatch.setattr(settings, "storage_retention_root", str(explicit), raising=False)
    monkeypatch.setattr(settings, "storage_retention_days", 7, raising=False)
    monkeypatch.setattr(settings, "storage_retention_enabled", True, raising=False)
    monkeypatch.setattr(settings, "storage_retention_include_plan_sync", False, raising=False)

    stats = storage_retention.cleanup_storage()

    assert stats["root"] == str(explicit)
    assert stats["ui_runs_deleted"] == 1


def test_missing_root_is_reported_without_raising(tmp_path, monkeypatch):
    """根目录不存在时不得抛错（清理失败不阻断应用）。"""
    monkeypatch.setattr(settings, "storage_retention_root", str(tmp_path / "nope"), raising=False)
    monkeypatch.setattr(settings, "storage_retention_days", 7, raising=False)
    monkeypatch.setattr(settings, "storage_retention_enabled", True, raising=False)
    monkeypatch.setattr(settings, "storage_retention_include_plan_sync", False, raising=False)

    stats = storage_retention.cleanup_storage()

    assert stats["ui_runs_deleted"] == 0
    assert "error" not in stats
