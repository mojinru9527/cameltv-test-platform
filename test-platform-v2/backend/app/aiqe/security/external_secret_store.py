"""V16-003-R4：外部 Secret Store 适配层（KMS/Secret Manager 抽象 + 加密文件后端）。

- 生产应使用云端 Secret Manager（AWS/GCP/Azure）或 KMS envelope；
- 本模块提供：
  * ``EncryptedFileStore``：Fernet 密钥来自环境变量（``AIQE_SECRET_STORE_KEY``），
    密文落盘、跨进程可解析，用于无云 SDK 的部署/测试；
  * ``AwsSecretsManagerStore``：真实 AWS Secrets Manager 适配器（可选依赖 boto3），
    不可用时 fail closed；
- 任何配置缺失/解密失败都必须抛错，禁止回退明文。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class ExternalStoreUnavailable(RuntimeError):
    """外部 Secret Store 不可用：调用方必须 fail closed。"""


@dataclass(frozen=True)
class SecretEntry:
    value: str
    expires_at: datetime
    run_id: str
    project_id: int


class EncryptedFileStore:
    """密文 JSON 文件存储：适用于无云 KMS 的单机/测试部署。"""

    def __init__(self, *, path: str | Path, key: str) -> None:
        raw_key = str(key or "").strip().encode()
        if not raw_key:
            raise ExternalStoreUnavailable(
                "AIQE_SECRET_STORE_KEY 未配置：外部 Secret Store 拒绝启动"
            )
        try:
            self._fernet = Fernet(raw_key)
        except (ValueError, TypeError) as exc:
            raise ExternalStoreUnavailable(f"AIQE_SECRET_STORE_KEY 非法: {exc}") from exc
        self._path = Path(path)
        self._lock = threading.RLock()

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExternalStoreUnavailable(f"Secret Store 读取失败: {exc}") from exc
        return dict(payload or {})

    def _write(self, payload: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            os.replace(tmp, self._path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def put(
        self,
        *,
        handle_id: str,
        value: str,
        expires_at: datetime,
        run_id: str,
        project_id: int,
    ) -> None:
        record = {
            "value": value,
            "expires_at": expires_at.isoformat(),
            "run_id": str(run_id),
            "project_id": int(project_id),
        }
        token = self._fernet.encrypt(
            json.dumps(record, ensure_ascii=False).encode("utf-8")
        ).decode()
        with self._lock:
            payload = self._read()
            payload[str(handle_id)] = token
            self._write(payload)

    def get(self, handle_id: str) -> SecretEntry | None:
        with self._lock:
            token = self._read().get(str(handle_id))
        if not token:
            return None
        try:
            record = json.loads(self._fernet.decrypt(token.encode()).decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise ExternalStoreUnavailable(
                "Secret Store 解密失败（密钥轮换/篡改）"
            ) from exc
        return SecretEntry(
            value=str(record.get("value") or ""),
            expires_at=datetime.fromisoformat(str(record.get("expires_at"))),
            run_id=str(record.get("run_id") or ""),
            project_id=int(record.get("project_id") or 0),
        )

    def drop(self, handle_id: str) -> None:
        with self._lock:
            payload = self._read()
            if str(handle_id) in payload:
                payload.pop(str(handle_id))
                self._write(payload)

    def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        removed = 0
        with self._lock:
            payload = self._read()
            for handle_id in list(payload.keys()):
                try:
                    entry = self.get(handle_id)
                except ExternalStoreUnavailable:
                    continue
                if entry is None or entry.expires_at <= moment:
                    payload.pop(handle_id, None)
                    removed += 1
            if removed:
                self._write(payload)
        return removed

    def clear(self) -> None:
        with self._lock:
            self._write({})


class AwsSecretsManagerStore:
    """AWS Secrets Manager 适配器（真实 KMS/托管存储；boto3 缺失即 fail closed）。"""

    def __init__(self, *, region: str = "", prefix: str = "aiqe/secrets") -> None:
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - 取决于部署依赖
            raise ExternalStoreUnavailable(
                "boto3 未安装：AWS Secrets Manager 不可用"
            ) from exc
        self._client = boto3.client("secretsmanager", region_name=region or None)
        self._prefix = prefix

    def _name(self, handle_id: str) -> str:
        return f"{self._prefix}/{handle_id}"

    def put(
        self,
        *,
        handle_id: str,
        value: str,
        expires_at: datetime,
        run_id: str,
        project_id: int,
    ) -> None:
        payload = json.dumps(
            {
                "value": value,
                "expires_at": expires_at.isoformat(),
                "run_id": run_id,
                "project_id": project_id,
            }
        )
        self._client.put_secret_value(SecretId=self._name(handle_id), SecretString=payload)

    def get(self, handle_id: str) -> SecretEntry | None:
        try:
            response = self._client.get_secret_value(SecretId=self._name(handle_id))
        except Exception as exc:
            name = type(exc).__name__
            if "ResourceNotFound" in name:
                return None
            raise ExternalStoreUnavailable(f"AWS Secrets Manager 读取失败: {name}") from exc
        record = json.loads(response.get("SecretString") or "{}")
        return SecretEntry(
            value=str(record.get("value") or ""),
            expires_at=datetime.fromisoformat(str(record.get("expires_at"))),
            run_id=str(record.get("run_id") or ""),
            project_id=int(record.get("project_id") or 0),
        )

    def drop(self, handle_id: str) -> None:
        try:
            self._client.delete_secret(SecretId=self._name(handle_id), ForceDeleteWithoutRecovery=True)
        except Exception as exc:
            if "ResourceNotFound" not in type(exc).__name__:
                raise ExternalStoreUnavailable("AWS Secrets Manager 删除失败") from exc

    def purge_expired(self, *, now: datetime | None = None) -> int:  # pragma: no cover - 云端
        return 0

    def clear(self) -> None:  # pragma: no cover - 云端
        raise ExternalStoreUnavailable("AWS Secrets Manager 不支持 clear")


def build_external_store() -> Any:
    """按配置构造外部 Store；缺配置/缺依赖一律 fail closed。"""
    from app.core.config import settings

    provider = str(getattr(settings, "aiqe_secret_store_provider", "file") or "file").lower()
    if provider == "aws":
        return AwsSecretsManagerStore(
            region=str(getattr(settings, "aiqe_secret_store_region", "") or ""),
            prefix=str(getattr(settings, "aiqe_secret_store_prefix", "aiqe/secrets") or "aiqe/secrets"),
        )
    if provider == "file":
        return EncryptedFileStore(
            path=str(
                getattr(settings, "aiqe_secret_store_path", "storage/secrets/aiqe-secrets.json")
            ),
            key=str(getattr(settings, "aiqe_secret_store_key", "") or ""),
        )
    raise ExternalStoreUnavailable(f"未知 Secret Store provider: {provider!r}")


__all__ = [
    "AwsSecretsManagerStore",
    "EncryptedFileStore",
    "ExternalStoreUnavailable",
    "SecretEntry",
    "build_external_store",
]
