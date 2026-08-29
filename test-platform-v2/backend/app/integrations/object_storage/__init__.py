"""Object storage factory (V31-003)."""
from __future__ import annotations

import os

from app.core.config import settings
from app.integrations.object_storage.base import (  # noqa: F401
    ObjectStorage,
    StorageError,
    sha256_bytes,
)
from app.integrations.object_storage.local import LocalStorage
from app.integrations.object_storage.s3 import S3Storage


def get_storage() -> ObjectStorage:
    """Return the configured provider (defaults to LocalStorage in dev/test)."""
    provider = (settings.object_storage_provider or "local").lower()
    if provider == "s3":
        bucket = settings.object_storage_s3_bucket
        if not bucket:
            raise StorageError(
                "object_storage_provider=s3 requires object_storage_s3_bucket"
            )
        return S3Storage(
            bucket=bucket,
            endpoint_url=settings.object_storage_s3_endpoint or None,
        )
    root = settings.object_storage_local_root or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "storage",
        "aitde-evidence",
    )
    return LocalStorage(root)


__all__ = [
    "ObjectStorage",
    "LocalStorage",
    "S3Storage",
    "StorageError",
    "sha256_bytes",
    "get_storage",
]
