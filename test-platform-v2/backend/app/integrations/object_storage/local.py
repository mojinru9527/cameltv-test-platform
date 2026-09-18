"""Local filesystem object storage provider (V31-003).

Dev/test default. Files are written under a base directory with the canonical
``/project/{p}/mission/{m}/run/{r}/{file}`` URI mapped onto the filesystem.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.integrations.object_storage.base import (
    ObjectStorage,
    StorageError,
    sha256_bytes,
)


class LocalStorage(ObjectStorage):
    provider_name = "local"

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def _path(self, uri: str) -> Path:
        """把对象 URI 收敛为 base 目录内的绝对路径（Batch 259 / B2-4，关闭审计 S4）。

        原实现 `normpath(join(base, rel))` 只做字符串归一，`../` 可以逃出 base。
        现规则：
          1. 反斜杠一律视为分隔符（Windows 客户端传来的 URI 不能与 Unix 语义分叉）；
          2. URI 中任何 `..` 段直接拒绝——不做"归一后再说"；
          3. 最后仍以 `resolve()` + `is_relative_to(base)` 兜底（符号链接同样逃不出去），
             写法与 `app/api/v1/lanhu_evidence_assets.py` 的下载收敛保持一致。

        注意：本模块的规范 URI 形如 `/project/{p}/mission/{m}/run/{r}/{file}`，
        因此**前导 `/` 是平台前缀而非绝对路径**，会被剥离后按相对路径处理。
        """
        raw = (uri or "").strip()
        if not raw:
            raise StorageError("对象 URI 不能为空")
        normalized = raw.replace("\\", "/").strip("/")
        segments = [seg for seg in normalized.split("/") if seg not in ("", ".")]
        if not segments or any(seg == ".." for seg in segments):
            raise StorageError(f"对象路径越权: {uri!r}")
        base = Path(self.base_dir).resolve()
        target = (base / Path(*segments)).resolve()
        if not target.is_relative_to(base):
            raise StorageError(f"对象路径越权: {uri!r}")
        return target

    def put(self, uri: str, data: bytes, content_type: str) -> dict[str, Any]:
        if not isinstance(data, (bytes, bytearray)):
            raise StorageError("LocalStorage.put expects bytes")
        path = self._path(uri)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(data))
        return {
            "uri": uri,
            "content_hash": sha256_bytes(bytes(data)),
            "content_type": content_type,
            "size_bytes": len(bytes(data)),
        }

    def get(self, uri: str) -> bytes:
        path = self._path(uri)
        if not path.exists():
            raise StorageError(f"object not found: {uri}")
        return path.read_bytes()

    def exists(self, uri: str) -> bool:
        return self._path(uri).exists()

    def delete(self, uri: str) -> None:
        path = self._path(uri)
        if path.exists():
            path.unlink()
