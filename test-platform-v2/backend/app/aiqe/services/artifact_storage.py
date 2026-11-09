"""M1 / TA-007：Artifact 存储后端抽象 + 本地 FS 实现。

TA-007 要求 driver 接口屏蔽后端差异（13 号 §4.12）：
- dev/test：本地 FS，`file://<root>/<sha256[:2]>/<sha256[2:4]>/<sha256>`；
- production：COS/MinIO/FS 三选一，由 TA-007 PoC 定；业务只依赖本接口。

安全：`read()` 只允许 root 下的文件（防路径穿越）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.config import settings


class ArtifactStorageError(RuntimeError):
    """存储层错误（越界/缺失/IO）。"""


class ArtifactStorageBackend(Protocol):
    def put(self, content: bytes, sha256_hex: str) -> str: ...

    def read(self, uri: str) -> bytes: ...


class LocalArtifactStorage:
    """本地文件系统后端（dev/test 默认）。"""

    def __init__(self, root: Path | None = None) -> None:
        base = getattr(settings, "storage_dir", None) or "storage"
        self.root = (root or (Path(base) / "artifacts")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, sha256_hex: str) -> Path:
        return self.root / sha256_hex[:2] / sha256_hex[2:4] / sha256_hex

    def put(self, content: bytes, sha256_hex: str) -> str:
        path = self._path_for(sha256_hex)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(content)
            tmp.replace(path)
        return f"file://{path}"

    def read(self, uri: str) -> bytes:
        if not uri.startswith("file://"):
            raise ArtifactStorageError(f"unsupported uri: {uri[:40]}")
        path = Path(uri.removeprefix("file://")).resolve()
        if not path.is_relative_to(self.root):
            raise ArtifactStorageError("artifact path escapes storage root")
        if not path.is_file():
            raise ArtifactStorageError("artifact file missing")
        return path.read_bytes()
