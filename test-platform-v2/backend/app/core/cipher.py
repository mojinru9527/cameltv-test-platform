"""Symmetric encryption for sensitive config values (environment variables, tokens).

Uses Fernet (AES-128-CBC via cryptography) with a key derived from app secret_key.

Batch 259 / B2-5（关闭审计 S5）：本模块是**唯一**的密钥派生实现。
`app/services/ai_config_service.py` 曾用 `secret_key` 自行派生 sha256 密钥（不是本模块的
`effective_secret_key`）——dev 下 `secret_key` 为空串，等价于用公开常量加密，
换 SECRET_KEY 后存量密文也解不开。现在该服务直接复用本模块，
并由 `assert_key_for_existing_ciphertext()` 在启动时兜底，杜绝静默数据损坏。
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


# ── 启动兜底：无 SECRET_KEY 但库中已有密文 → fail-fast（Batch 259 / B2-5）──
# (模型路径, 类名, 表名, 密文列名)
_CIPHERTEXT_SOURCES: tuple[tuple[str, str, str, str], ...] = (
    ("app.models.ai_provider", "AiProvider", "ai_provider", "api_key_encrypted"),
    (
        "app.models.wiki",
        "ExternalWikiConnection",
        "external_wiki_connection",
        "token_encrypted",
    ),
)


def ciphertext_sources(db) -> list[str]:
    """返回当前库中**确实存有密文**的来源（表名.列名）；空列表 = 没有密文。"""
    from sqlalchemy import func, select

    found: list[str] = []
    for module_path, class_name, table_name, column_name in _CIPHERTEXT_SOURCES:
        module = __import__(module_path, fromlist=[class_name])
        model = getattr(module, class_name)
        column = getattr(model, column_name)
        count = db.scalar(
            select(func.count())
            .select_from(model)
            .where(column.is_not(None), column != "")
        ) or 0
        if count:
            found.append(f"{table_name}.{column_name}")
    return found


def assert_key_for_existing_ciphertext(db) -> None:
    """未配置 SECRET_KEY 却已有密文时拒绝启动。

    原因：dev 环境 `effective_secret_key` 每次进程启动随机生成。此时若拿它去解已有密文，
    等于静默换了一套密钥——存量密文永远解不开，且没有任何报错。宁可启动失败，
    也不要静默数据损坏（错误文案给出可执行的两种修法）。
    """
    if settings.secret_key:
        return
    sources = ciphertext_sources(db)
    if not sources:
        return
    raise RuntimeError(
        "SECRET_KEY 未配置，但数据库中已存在密文（" + "、".join(sources) + "）。"
        "继续启动会使用一次性开发密钥，导致这些密文永久无法解密。"
        "请配置 SECRET_KEY（推荐复用原值），或先清理对应密文后再启动。"
    )
