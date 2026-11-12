"""M2 / batch-285：MinIO（S3 兼容）Artifact 存储后端。

不引入 boto3/minio SDK：用 httpx + AWS SigV4 直连，避免新增带哈希锁的依赖。
URI：`s3://<bucket>/<key>`；key 与本地 FS 一致：`<sha[:2]>/<sha[2:4]>/<sha>`。
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

import httpx

from app.aiqe.services.artifact_storage import ArtifactStorageError


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, datestamp: str, region: str) -> bytes:
    k_date = _hmac(("AWS4" + secret).encode("utf-8"), datestamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, "s3")
    return _hmac(k_service, "aws4_request")


def sigv4_headers(
    method: str,
    url: str,
    payload: bytes,
    *,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
) -> dict[str, str]:
    parsed = urlsplit(url)
    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    payload_hash = _sha256_hex(payload)
    canonical_uri = quote(parsed.path or "/", safe="/-_.~")
    canonical_query = parsed.query
    canonical_headers = (
        f"host:{parsed.netloc}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = (
        f"{method}\n{canonical_uri}\n{canonical_query}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    scope = f"{datestamp}/{region}/s3/aws4_request"
    string_to_sign = (
        "AWS4-HMAC-SHA256\n"
        f"{amz_date}\n{scope}\n{_sha256_hex(canonical_request.encode('utf-8'))}"
    )
    signature = hmac.new(
        _signing_key(secret_key, datestamp, region),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
    }


class MinioArtifactStorage:
    def __init__(
        self,
        endpoint: str,
        *,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        client: httpx.Client | None = None,
    ) -> None:
        if not endpoint:
            raise ArtifactStorageError("MINIO_ENDPOINT 未配置")
        if not access_key or not secret_key:
            raise ArtifactStorageError("MINIO_ACCESS_KEY/SECRET_KEY 未配置")
        self.endpoint = endpoint.rstrip("/")
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self._client = client or httpx.Client(timeout=30)

    def _url(self, key: str = "") -> str:
        base = f"{self.endpoint}/{quote(self.bucket, safe='')}"
        return f"{base}/{key}" if key else base

    def ensure_bucket(self) -> None:
        resp = self._client.put(
            self._url(),
            headers=sigv4_headers(
                "PUT",
                self._url(),
                b"",
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
            ),
        )
        if resp.status_code not in (200, 409):
            raise ArtifactStorageError(
                f"MinIO ensure_bucket 失败: {resp.status_code} {resp.text[:200]}"
            )

    def put(self, content: bytes, sha256_hex: str) -> str:
        key = f"{sha256_hex[:2]}/{sha256_hex[2:4]}/{sha256_hex}"
        url = self._url(key)
        resp = self._client.put(
            url,
            content=content,
            headers=sigv4_headers(
                "PUT",
                url,
                content,
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
            ),
        )
        if resp.status_code not in (200, 201):
            raise ArtifactStorageError(
                f"MinIO put 失败: {resp.status_code} {resp.text[:200]}"
            )
        return f"s3://{self.bucket}/{key}"

    def read(self, uri: str) -> bytes:
        prefix = f"s3://{self.bucket}/"
        if not uri.startswith(prefix):
            raise ArtifactStorageError(f"不支持的 uri: {uri[:60]}")
        key = uri[len(prefix) :]
        url = self._url(key)
        resp = self._client.get(
            url,
            headers=sigv4_headers(
                "GET",
                url,
                b"",
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
            ),
        )
        if resp.status_code == 404:
            raise ArtifactStorageError("artifact 不存在于 MinIO")
        if resp.status_code != 200:
            raise ArtifactStorageError(
                f"MinIO get 失败: {resp.status_code} {resp.text[:200]}"
            )
        return resp.content

    def delete(self, uri: str) -> None:
        prefix = f"s3://{self.bucket}/"
        if not uri.startswith(prefix):
            raise ArtifactStorageError(f"不支持的 uri: {uri[:60]}")
        key = uri[len(prefix) :]
        url = self._url(key)
        resp = self._client.delete(
            url,
            headers=sigv4_headers(
                "DELETE",
                url,
                b"",
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
            ),
        )
        if resp.status_code not in (200, 204, 404):
            raise ArtifactStorageError(
                f"MinIO delete 失败: {resp.status_code} {resp.text[:200]}"
            )
