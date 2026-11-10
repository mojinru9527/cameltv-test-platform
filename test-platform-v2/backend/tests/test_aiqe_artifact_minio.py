"""M2 / batch-285：MinIO Artifact 存储后端单测（httpx mock，不依赖真实 MinIO）。"""
from __future__ import annotations

import hashlib

import httpx
import pytest

from app.aiqe.models.run import TestRun
from app.aiqe.services.artifact_service import put_artifact, read_artifact
from app.aiqe.services.artifact_storage import ArtifactStorageError, LocalArtifactStorage
from app.aiqe.services.artifact_storage import get_storage_backend
from app.aiqe.services.artifact_storage_minio import MinioArtifactStorage


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.requests: list[httpx.Request] = []
        self.bucket_status = 200

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "PUT" and path.rstrip("/").endswith("/cameltv-artifacts"):
            return httpx.Response(self.bucket_status, request=request)
        if request.method == "PUT":
            self.objects[path] = request.read()
            return httpx.Response(200, request=request)
        if request.method == "GET":
            if path in self.objects:
                return httpx.Response(200, content=self.objects[path], request=request)
            return httpx.Response(404, request=request)
        return httpx.Response(405, request=request)


def make_storage() -> tuple[MinioArtifactStorage, _Transport]:
    transport = _Transport()
    client = httpx.Client(transport=transport)
    storage = MinioArtifactStorage(
        "http://minio:9000",
        access_key="ak",
        secret_key="sk",
        bucket="cameltv-artifacts",
        client=client,
    )
    return storage, transport


def test_put_and_read_roundtrip():
    storage, transport = make_storage()
    content = b"minio-artifact"
    digest = hashlib.sha256(content).hexdigest()

    uri = storage.put(content, digest)
    assert uri == f"s3://cameltv-artifacts/{digest[:2]}/{digest[2:4]}/{digest}"
    assert storage.read(uri) == content

    auth = transport.requests[0].headers["Authorization"]
    assert auth.startswith("AWS4-HMAC-SHA256 Credential=ak/")
    assert transport.requests[0].headers["x-amz-content-sha256"] == digest


def test_read_missing_raises():
    storage, _ = make_storage()
    with pytest.raises(ArtifactStorageError):
        storage.read("s3://cameltv-artifacts/aa/bb/missing")


def test_ensure_bucket_accepts_409():
    storage, transport = make_storage()
    transport.bucket_status = 409
    storage.ensure_bucket()


def test_factory_selects_backend(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "artifact_storage_backend", "fs")
    assert isinstance(get_storage_backend(), LocalArtifactStorage)

    monkeypatch.setattr(settings, "artifact_storage_backend", "minio")
    monkeypatch.setattr(settings, "minio_endpoint", "http://minio:9000")
    monkeypatch.setattr(settings, "minio_access_key", "ak")
    monkeypatch.setattr(settings, "minio_secret_key", "sk")
    assert isinstance(get_storage_backend(), MinioArtifactStorage)


def test_artifact_service_uses_minio(db_session, monkeypatch):
    from app.core.config import settings

    storage, _transport = make_storage()
    monkeypatch.setattr(settings, "artifact_storage_backend", "minio")
    monkeypatch.setattr(settings, "minio_endpoint", "http://minio:9000")
    monkeypatch.setattr(settings, "minio_access_key", "ak")
    monkeypatch.setattr(settings, "minio_secret_key", "sk")

    run = TestRun(project_id=1, run_key="RUN-MINIO-1", source_type="manual", status="RUNNING")
    db_session.add(run)
    db_session.flush()
    row = put_artifact(
        db_session,
        project_id=1,
        run_id=run.id,
        content=b"trace-bytes",
        artifact_type="trace",
        storage=storage,
    )
    db_session.commit()
    assert row.storage_uri.startswith("s3://cameltv-artifacts/")
    assert read_artifact(db_session, row.id, 1, storage=storage) == b"trace-bytes"
