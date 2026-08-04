"""Symmetric encryption for sensitive config values (environment variables, tokens).

Uses Fernet (AES-128-CBC via cryptography) with a key derived from app secret_key.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a 32-byte Fernet key from the app secret key.

    Batch 80（C79-1）：移除硬编码回退密钥（Batch 37 P1-01）。
    开发环境走 `effective_secret_key` 自动生成会话密钥；生产环境未配置 SECRET_KEY 时直接失败。
    """
    key = settings.effective_secret_key
    if not key:
        raise RuntimeError("SECRET_KEY 未配置且当前环境不允许自动生成，禁止加密/解密")
    raw = key.encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key_b64 = base64.urlsafe_b64encode(digest)
    return Fernet(key_b64)


def encrypt_value(plain: str) -> str:
    """Encrypt a plaintext string → base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet ciphertext → plaintext string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
