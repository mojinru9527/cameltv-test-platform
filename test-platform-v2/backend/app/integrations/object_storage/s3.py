"""S3 / MinIO object storage provider (V31-003).

Uses boto3 lazily so the module imports cleanly in dev/test without an AWS SDK.
Production deployments set AWS_ENDPOINT_URL / AWS_BUCKET to point at MinIO.
"""
from __future__ import annotations

from typing import Any

from app.integrations.object_storage.base import ObjectStorage, StorageError, sha256_bytes


def _client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - env dependent
        raise StorageError("boto3 is not installed; cannot use S3 storage") from exc
    return boto3.client(
        "s3",
        endpoint_url=None,
        region_name=None,
    )


class S3Storage(ObjectStorage):
    provider_name = "s3"

    def __init__(self, bucket: str, endpoint_url: str | None = None) -> None:
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self._client: Any | None = None

    def _s3(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - env dependent
                raise StorageError("boto3 is not installed") from exc
            kwargs: dict[str, Any] = {}
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url
            self._client = boto3.client("s3", **kwargs)
        return self._client

    def _key(self, uri: str) -> str:
        return uri.strip("/")

    def put(self, uri: str, data: bytes, content_type: str) -> dict[str, Any]:
        if not isinstance(data, (bytes, bytearray)):
            raise StorageError("S3Storage.put expects bytes")
        try:
            self._s3().put_object(
                Bucket=self.bucket, Key=self._key(uri), Body=bytes(data),
                ContentType=content_type,
            )
        except Exception as exc:  # pragma: no cover - network
            raise StorageError(f"s3 put failed: {exc}") from exc
        return {
            "uri": uri,
            "content_hash": sha256_bytes(bytes(data)),
            "content_type": content_type,
            "size_bytes": len(bytes(data)),
        }

    def get(self, uri: str) -> bytes:
        try:
            import io
            stream = io.BytesIO()
            self._s3().download_fileobj(Bucket=self.bucket, Key=self._key(uri), Fileobj=stream)
            return stream.getvalue()
        except Exception as exc:  # pragma: no cover - network
            raise StorageError(f"s3 get failed: {exc}") from exc

    def exists(self, uri: str) -> bool:
        try:
            self._s3().head_object(Bucket=self.bucket, Key=self._key(uri))
            return True
        except Exception:  # pragma: no cover - network
            return False

    def delete(self, uri: str) -> None:
        try:
            self._s3().delete_object(Bucket=self.bucket, Key=self._key(uri))
        except Exception as exc:  # pragma: no cover - network
            raise StorageError(f"s3 delete failed: {exc}") from exc
