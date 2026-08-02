"""Batch 63 Slice 1 — JWT 契约测试（python-jose -> PyJWT 替换后保持行为一致）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from app.core.security import create_access_token, decode_token


def test_create_and_decode_roundtrip(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "batch63-test-secret")
    from app.core.config import settings

    monkeypatch.setattr(settings, "effective_secret_key", "batch63-test-secret")
    token = create_access_token(subject=42, extra={"role": "admin"})

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_token_is_standard_pyjwt_decodable(monkeypatch):
    """替换后产物必须是标准 JWT，可由 PyJWT 直接校验，防止隐式降级为明文。"""
    monkeypatch.setenv("SECRET_KEY", "batch63-test-secret")
    from app.core.config import settings

    monkeypatch.setattr(settings, "effective_secret_key", "batch63-test-secret")
    token = create_access_token(subject="u-1")

    decoded = pyjwt.decode(
        token,
        "batch63-test-secret",
        algorithms=[settings.algorithm],
    )
    assert decoded["sub"] == "u-1"


def test_expired_token_returns_none(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "batch63-test-secret")
    from app.core.config import settings

    monkeypatch.setattr(settings, "effective_secret_key", "batch63-test-secret")
    expired = pyjwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "batch63-test-secret",
        algorithm="HS256",
    )
    assert decode_token(expired) is None


def test_tampered_token_returns_none(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "batch63-test-secret")
    from app.core.config import settings

    monkeypatch.setattr(settings, "effective_secret_key", "batch63-test-secret")
    token = create_access_token(subject="1")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert decode_token(tampered) is None


def test_wrong_secret_returns_none(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "batch63-test-secret")
    from app.core.config import settings

    monkeypatch.setattr(settings, "effective_secret_key", "batch63-test-secret")
    token = create_access_token(subject="1")

    monkeypatch.setattr(settings, "effective_secret_key", "another-secret")
    assert decode_token(token) is None


def test_algorithm_claim_is_hs256(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "batch63-test-secret")
    from app.core.config import settings

    monkeypatch.setattr(settings, "effective_secret_key", "batch63-test-secret")
    token = create_access_token(subject="1")
    header = pyjwt.get_unverified_header(token)
    assert header.get("alg") == "HS256"
