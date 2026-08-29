"""Object storage abstraction (V31-003).

A minimal provider interface so Evidence can store raw bytes in Local FS, S3 or
MinIO without coupling to any vendor SDK. DB stores only ``storage_uri`` +
``content_hash`` + ``content_type`` + ``size_bytes``; the object itself lives here.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any


class StorageError(Exception):
    """Raised for any object-storage failure. Callers must not mark evidence
    COMPLETE when a put/read fails."""


def sha256_bytes(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class ObjectStorage(ABC):
    provider_name: str = "base"

    @abstractmethod
    def put(self, uri: str, data: bytes, content_type: str) -> dict[str, Any]:
        """Store ``data`` and return {uri, content_hash, content_type, size_bytes}."""

    @abstractmethod
    def get(self, uri: str) -> bytes:
        """Read bytes back; raise StorageError if missing."""

    @abstractmethod
    def exists(self, uri: str) -> bool:
        ...

    @abstractmethod
    def delete(self, uri: str) -> None:
        ...

    def make_uri(self, project_id: int, mission_id: int, run_id: int, filename: str) -> str:
        """Canonical run-scoped URI: /project/{p}/mission/{m}/run/{r}/{filename}."""
        safe = str(filename).replace("\\", "/").lstrip("/")
        return f"/project/{project_id}/mission/{mission_id}/run/{run_id}/{safe}"

    def build(self, uri: str, data: bytes, content_type: str) -> dict[str, Any]:
        """Wrap put with hash+sizing and store metadata only."""
        info = self.put(uri, data, content_type)
        return {
            "storage_uri": info["uri"],
            "content_hash": info.get("content_hash") or sha256_bytes(data),
            "content_type": info.get("content_type") or content_type,
            "size_bytes": info.get("size_bytes") or len(data),
        }
