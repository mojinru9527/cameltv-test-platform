"""证据打包（Batch 258 / B1-5）：本地目录 → (文件名, 字节) 列表 + sha256 清单。

本地先算一份 sha256，上传后与平台 manifest 对账，避免"传上去了但其实截断了"。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

MANIFEST_NAME = "manifest.json"
MAX_FILES = 200


def collect_files(directory: str | Path) -> list[tuple[str, bytes]]:
    """收集目录下的证据文件（跳过 manifest.json 自身）。"""
    base = Path(directory)
    if not base.is_dir():
        raise FileNotFoundError(f"证据目录不存在: {base}")
    files: list[tuple[str, bytes]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_NAME:
            continue
        files.append((path.name, path.read_bytes()))
        if len(files) > MAX_FILES:
            raise ValueError(f"证据文件数超过上限 {MAX_FILES}")
    if not files:
        raise ValueError(f"证据目录为空: {base}")
    return files


def local_manifest(files: list[tuple[str, bytes]]) -> dict:
    entries = [
        {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in files
    ]
    return {
        "file_count": len(entries),
        "total_bytes": sum(entry["size"] for entry in entries),
        "files": sorted(entries, key=lambda entry: entry["name"]),
    }


def verify_against(remote_manifest: dict, local: dict) -> list[str]:
    """返回不一致项的描述；空列表 = 完全一致。"""
    problems: list[str] = []
    remote_files = {entry["name"]: entry for entry in remote_manifest.get("files", [])}
    local_files = {entry["name"]: entry for entry in local.get("files", [])}
    for name, entry in local_files.items():
        remote = remote_files.get(name)
        if remote is None:
            problems.append(f"平台缺少文件: {name}")
            continue
        if remote.get("sha256") != entry["sha256"]:
            problems.append(f"sha256 不一致: {name}")
    for name in remote_files:
        if name not in local_files:
            problems.append(f"平台多出文件: {name}")
    return problems
