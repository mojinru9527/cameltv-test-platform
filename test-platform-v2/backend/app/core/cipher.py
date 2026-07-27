"""Symmetric encryption for sensitive config values (environment variables, tokens).

Uses Fernet (AES-128-CBC via cryptography) with a key derived from app secret_key.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a 32-byte Fernet key from the app secret_key."""
    raw = settings.secret_key.encode("utf-8") if settings.secret_key else b"cameltv-dev-key"
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(plain: str) -> str:
    """Encrypt a plaintext string → base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet ciphertext → plaintext string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
