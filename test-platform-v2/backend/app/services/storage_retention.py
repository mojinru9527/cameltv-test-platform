"""存储保留期清理（生产磁盘防护）。

背景：生产持久卷（`/app/storage`）曾因 UI 测试产物累积写满。本服务按 mtime
清理超过 `storage_retention_days` 天的旧产物：

- `{root}/ui-runs/<数字运行id>/`：UI 测试运行产物（截图/录像，最大占用源）；
  只清理纯数字目录，`plan-sync`（计划执行逐用例产物，与历史计划关联）仅在
  `STORAGE_RETENTION_INCLUDE_PLAN_SYNC=true` 时按同一保留期清理。

删除只依据目录 mtime（运行中任务 mtime 必然是近期的，天然跳过）。

根目录由 `storage_retention_root` 指定；为空时取 `<backend>/storage`
（与 `playwright_executor.STORAGE_DIR` 同一约定；容器内即 `/app/storage`）。

平台简化批次：DSH 任务体系已删除，其 `dsh-sessions/workspaces` 与会话 jsonl
清理分支随模块一并移除。
"""
from __future__ import annotations

import logging
import re
import shutil
import time
from pathlib import Path
from collections.abc import Callable

from app.core.config import settings

logger = logging.getLogger(__name__)

_NUMERIC_DIR = re.compile(r"^\d+$")

# 与 playwright_executor.STORAGE_DIR 同源：backend/storage（容器内 /app/storage）
_DEFAULT_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"


def _storage_root() -> Path:
    """保留期清理根目录（含 ui-runs 子目录）。"""
    explicit = (settings.storage_retention_root or "").strip()
    if explicit:
        return Path(explicit)
    return _DEFAULT_STORAGE_ROOT


def _older_than(cutoff: float) -> Callable[[Path], bool]:
    return lambda path: path.stat().st_mtime < cutoff


def _purge_dirs(root: Path, matcher: re.Pattern[str], cutoff: float) -> tuple[int, int]:
    """删除 root 下匹配 matcher 的过期目录；返回 (删除数, 释放字节)。"""
    if not root.is_dir():
        return 0, 0
    deleted = 0
    freed = 0
    for child in root.iterdir():
        try:
            if not child.is_dir() or not matcher.fullmatch(child.name):
                continue
            try:
                mtime = child.stat().st_mtime
            except OSError:
                continue
            if not _older_than(cutoff)(child):
                continue
            size = _dir_size(child)
            shutil.rmtree(child, ignore_errors=True)
            if not child.exists():
                deleted += 1
                freed += size
                logger.info(
                    "[storage-retention] removed %s (%.1f MB, mtime %s)",
                    child,
                    size / 1024 / 1024,
                    time.strftime("%Y-%m-%d", time.localtime(mtime)),
                )
        except OSError as exc:
            logger.warning("[storage-retention] skip %s: %s", child, exc)
    return deleted, freed


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def cleanup_storage() -> dict:
    """执行一次保留期清理，返回统计（幂等，可每日/启动调用）。"""
    retention_days = max(int(settings.storage_retention_days), 1)
    cutoff = time.time() - retention_days * 86400
    root = _storage_root()

    stats: dict = {
        "enabled": settings.storage_retention_enabled,
        "retention_days": retention_days,
        "root": str(root),
        "ui_runs_deleted": 0,
        "ui_runs_freed_mb": 0.0,
    }

    try:
        ui_deleted, ui_freed = _purge_dirs(root / "ui-runs", _NUMERIC_DIR, cutoff)

        # plan-sync（计划执行逐用例产物）与历史计划记录关联，默认不清理；
        # 显式开启 STORAGE_RETENTION_INCLUDE_PLAN_SYNC=true 后按同一保留期清理。
        ps_deleted = 0
        ps_freed = 0
        if settings.storage_retention_include_plan_sync:
            plan_sync_root = root / "ui-runs" / "plan-sync"
            if plan_sync_root.is_dir():
                for child in plan_sync_root.iterdir():
                    try:
                        if not child.is_dir():
                            continue
                        mtime = child.stat().st_mtime
                        if mtime >= cutoff:
                            continue
                        size = _dir_size(child)
                        shutil.rmtree(child, ignore_errors=True)
                        if not child.exists():
                            ps_deleted += 1
                            ps_freed += size
                    except OSError as exc:
                        logger.warning(
                            "[storage-retention] skip plan-sync %s: %s", child, exc
                        )

        stats["ui_runs_deleted"] = ui_deleted
        stats["ui_runs_freed_mb"] = round(ui_freed / 1024 / 1024, 1)
        stats["plan_sync_deleted"] = ps_deleted
        stats["plan_sync_freed_mb"] = round(ps_freed / 1024 / 1024, 1)
    except Exception as exc:
        logger.exception("[storage-retention] cleanup failed: %s", exc)
        stats["error"] = str(exc)[:500]

    total_mb = round(
        stats["ui_runs_freed_mb"] + stats["plan_sync_freed_mb"],
        1,
    )
    stats["total_freed_mb"] = total_mb
    logger.info(
        "[storage-retention] done: ui_runs=%s plan_sync=%s freed=%.1f MB",
        stats["ui_runs_deleted"],
        stats["plan_sync_deleted"],
        total_mb,
    )
    return stats
