"""存储保留期清理（生产磁盘防护）— Batch fix。

背景：生产 Railway 卷（/app/storage，默认仅 434M）曾因 DSH 任务工作区与
UI 测试产物累积写满，导致新建 DSH 任务 ENOSPC。本服务按 mtime 清理
超过 `storage_retention_days` 天的旧产物：

- `{root}/ui-runs/<数字运行id>/`：UI 测试运行产物（截图/录像，最大占用源）；
  只清理纯数字目录，`plan-sync`（计划执行逐用例产物，与历史计划关联）默认不清理。
- `{root}/dsh-sessions/workspaces/ws-*`：DSH 任务隔离工作区。
- `{root}/dsh-sessions/*.jsonl*`：DSH 会话日志。

删除只依据目录/文件 mtime（运行中任务 mtime 必然是近期的，天然跳过）。
根目录由 `storage_retention_root` 指定；为空时复用 `dsh_session_root` 的父目录
（生产为 /app/storage），与 DSH runner 的默认根同源。
"""
from __future__ import annotations

import logging
import re
import shutil
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_NUMERIC_DIR = re.compile(r"^\d+$")
_WS_DIR = re.compile(r"^ws-[0-9a-f]+$")


def _storage_root() -> Path:
    """保留期清理根目录（含 ui-runs / dsh-sessions 等子目录）。"""
    explicit = (settings.storage_retention_root or "").strip()
    if explicit:
        return Path(explicit)
    # 与 DSH runner 默认会话根同源（backend/storage/dsh-sessions 的父目录）
    from app.services.dsh.dsh_runner import _session_root

    return _session_root().parent


def _older_than(cutoff: float) -> bool:
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
        except OSError as exc:  # noqa: PERF203 - 单个失败不中断整体清理
            logger.warning("[storage-retention] skip %s: %s", child, exc)
    return deleted, freed


def _purge_files(root: Path, suffix: str, cutoff: float) -> tuple[int, int]:
    """删除 root 下匹配后缀的过期文件（如 *.jsonl*）。"""
    if not root.is_dir():
        return 0, 0
    deleted = 0
    freed = 0
    for child in root.iterdir():
        try:
            if not child.is_file() or suffix not in child.name:
                continue
            if not _older_than(cutoff)(child):
                continue
            size = child.stat().st_size
            child.unlink(missing_ok=True)
            deleted += 1
            freed += size
            logger.info("[storage-retention] removed %s (%.1f KB)", child, size / 1024)
        except OSError as exc:  # noqa: PERF203
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
        "workspaces_deleted": 0,
        "workspaces_freed_mb": 0.0,
        "session_files_deleted": 0,
        "session_files_freed_mb": 0.0,
    }

    try:
        ui_deleted, ui_freed = _purge_dirs(root / "ui-runs", _NUMERIC_DIR, cutoff)
        ws_deleted, ws_freed = _purge_dirs(
            root / "dsh-sessions" / "workspaces", _WS_DIR, cutoff
        )
        sf_deleted, sf_freed = _purge_files(root / "dsh-sessions", ".jsonl", cutoff)

        stats["ui_runs_deleted"] = ui_deleted
        stats["ui_runs_freed_mb"] = round(ui_freed / 1024 / 1024, 1)
        stats["workspaces_deleted"] = ws_deleted
        stats["workspaces_freed_mb"] = round(ws_freed / 1024 / 1024, 1)
        stats["session_files_deleted"] = sf_deleted
        stats["session_files_freed_mb"] = round(sf_freed / 1024 / 1024, 1)
    except Exception as exc:  # noqa: BLE001 - 清理失败不阻断应用
        logger.exception("[storage-retention] cleanup failed: %s", exc)
        stats["error"] = str(exc)[:500]

    total_mb = round(
        sum(
            [
                stats["ui_runs_freed_mb"],
                stats["workspaces_freed_mb"],
                stats["session_files_freed_mb"],
            ]
        ),
        1,
    )
    stats["total_freed_mb"] = total_mb
    logger.info(
        "[storage-retention] done: ui_runs=%s workspaces=%s "
        "session_files=%s freed=%.1f MB",
        stats["ui_runs_deleted"],
        stats["workspaces_deleted"],
        stats["session_files_deleted"],
        total_mb,
    )
    return stats
