"""存储保留期清理（生产磁盘防护）回归测试。

覆盖：
- ui-runs 纯数字运行目录：过期删除、新目录保留、非数字目录（plan-sync）不动
- dsh-sessions/workspaces 的 ws-* 工作区：过期删除、新目录保留
- dsh-sessions 会话 jsonl：过期删除、新文件保留
- 缺失根目录 / 空目录：安全返回 0，不抛错
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.services.storage_retention import cleanup_storage

OLD = time.time() - 30 * 86400  # 30 天前（超过 7 天保留期）
NEW = time.time() - 3600        # 1 小时前（保留）


def _age(path: Path, ts: float) -> None:
    os.utime(path, (ts, ts))


def _make_dirs(*paths: Path) -> list[Path]:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
    return list(paths)


class TestUiRunsCleanup:
    def test_old_numeric_runs_deleted_new_kept(self, tmp_path):
        """过期纯数字运行目录删除，近期运行目录保留。"""
        old_run = _make_dirs(tmp_path / "ui-runs" / "12")[0]
        new_run = _make_dirs(tmp_path / "ui-runs" / "99")[0]
        # 2MB 文件，保证 freed_mb 可断言
        (old_run / "shot.png").write_bytes(b"x" * (2 * 1024 * 1024))
        (new_run / "shot.png").write_bytes(b"x" * 1024)
        _age(old_run, OLD)
        _age(new_run, NEW)

        with patch.object(settings, "storage_retention_root", str(tmp_path)), \
                patch.object(settings, "storage_retention_days", 7):
            stats = cleanup_storage()

        assert stats["ui_runs_deleted"] == 1
        assert stats["ui_runs_freed_mb"] > 0
        assert not old_run.exists()
        assert new_run.exists()

    def test_plan_sync_untouched(self, tmp_path):
        """plan-sync（计划执行逐用例产物，与历史计划关联）默认不清理。"""
        plan = _make_dirs(tmp_path / "ui-runs" / "plan-sync" / "TC-10001")[0]
        _age(plan, OLD)

        with patch.object(settings, "storage_retention_root", str(tmp_path)), \
                patch.object(settings, "storage_retention_days", 7):
            stats = cleanup_storage()

        assert stats["ui_runs_deleted"] == 0
        assert stats["plan_sync_deleted"] == 0
        assert plan.exists()

    def test_plan_sync_cleanup_when_enabled(self, tmp_path):
        """STORAGE_RETENTION_INCLUDE_PLAN_SYNC=true 时按同一保留期清理过期子目录。"""
        old_plan = _make_dirs(tmp_path / "ui-runs" / "plan-sync" / "TC-10001")[0]
        new_plan = _make_dirs(tmp_path / "ui-runs" / "plan-sync" / "SP-B130-XYZ")[0]
        _age(old_plan, OLD)
        _age(new_plan, NEW)

        with patch.object(settings, "storage_retention_root", str(tmp_path)), \
                patch.object(settings, "storage_retention_days", 7), \
                patch.object(settings, "storage_retention_include_plan_sync", True):
            stats = cleanup_storage()

        assert stats["plan_sync_deleted"] == 1
        assert not old_plan.exists()
        assert new_plan.exists()


class TestDshSessionsCleanup:
    def test_old_workspace_deleted_new_kept(self, tmp_path):
        """过期 ws-* 工作区删除，近期工作区保留。"""
        old_ws = _make_dirs(tmp_path / "dsh-sessions" / "workspaces" / "ws-aaaa1111")[0]
        new_ws = _make_dirs(tmp_path / "dsh-sessions" / "workspaces" / "ws-bbbb2222")[0]
        _age(old_ws, OLD)
        _age(new_ws, NEW)

        with patch.object(settings, "storage_retention_root", str(tmp_path)), \
                patch.object(settings, "storage_retention_days", 7):
            stats = cleanup_storage()

        assert stats["workspaces_deleted"] == 1
        assert not old_ws.exists()
        assert new_ws.exists()

    def test_old_session_jsonl_deleted_new_kept(self, tmp_path):
        """过期会话 jsonl 删除，近期会话保留；非 jsonl 文件不动。"""
        sess = _make_dirs(tmp_path / "dsh-sessions")[0]
        old_log = sess / "session-old.jsonl"
        new_log = sess / "session-new.jsonl"
        other = sess / "readme.txt"
        old_log.write_text("x" * 512)
        new_log.write_text("y" * 512)
        other.write_text("keep")
        _age(old_log, OLD)
        _age(new_log, NEW)
        _age(other, OLD)

        with patch.object(settings, "storage_retention_root", str(tmp_path)), \
                patch.object(settings, "storage_retention_days", 7):
            stats = cleanup_storage()

        assert stats["session_files_deleted"] == 1
        assert not old_log.exists()
        assert new_log.exists()
        assert other.exists()


class TestRobustness:
    def test_missing_roots_safe(self, tmp_path):
        """根目录缺失时安全返回 0，不抛错。"""
        with patch.object(settings, "storage_retention_root", str(tmp_path / "nope")), \
                patch.object(settings, "storage_retention_days", 7):
            stats = cleanup_storage()

        assert stats["ui_runs_deleted"] == 0
        assert stats["workspaces_deleted"] == 0
        assert stats["session_files_deleted"] == 0
        assert stats["total_freed_mb"] == 0

    def test_default_root_derived_from_dsh_session_root(self, tmp_path, monkeypatch):
        """未配置 retention_root 时，根 = dsh_session_root 的父目录。"""
        monkeypatch.setattr(settings, "storage_retention_root", "")
        monkeypatch.setattr(
            settings, "dsh_session_root", str(tmp_path / "dsh-sessions")
        )
        run_dir = _make_dirs(tmp_path / "ui-runs" / "5")[0]
        _age(run_dir, OLD)

        stats = cleanup_storage()

        assert stats["root"] == str(tmp_path)
        assert stats["ui_runs_deleted"] == 1
        assert not run_dir.exists()
