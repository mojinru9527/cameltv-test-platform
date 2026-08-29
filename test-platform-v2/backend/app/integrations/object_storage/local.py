"""Local filesystem object storage provider (V31-003).

Dev/test default. Files are written under a base directory with the canonical
``/project/{p}/mission/{m}/run/{r}/{file}`` URI mapped onto the filesystem.
"""
from __future__ import annotations

import os
from typing import Any

from app.integrations.object_storage.base import ObjectStorage, StorageError, sha256_bytes


class LocalStorage(ObjectStorage):
    provider_name = "local"

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def _path(self, uri: str) -> str:
        rel = uri.strip("/")
        return os.path.normpath(os.path.join(self.base_dir, rel.replace("/", os.sep)))

    def put(self, uri: str, data: bytes, content_type: str) -> dict[str, Any]:
        if not isinstance(data, (bytes, bytearray)):
            raise StorageError("LocalStorage.put expects bytes")
        path = self._path(uri)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return {
            "uri": uri,
            "content_hash": sha256_bytes(bytes(data)),
            "content_type": content_type,
            "size_bytes": len(bytes(data)),
        }

    def get(self, uri: str) -> bytes:
        path = self._path(uri)
        if not os.path.exists(path):
            raise StorageError(f"object not found: {uri}")
        with open(path, "rb") as fh:
            return fh.read()

    def exists(self, uri: str) -> bool:
        return os.path.exists(self._path(uri))

    def delete(self, uri: str) -> None:
        path = self._path(uri)
        if os.path.exists(path):
            os.remove(path)
