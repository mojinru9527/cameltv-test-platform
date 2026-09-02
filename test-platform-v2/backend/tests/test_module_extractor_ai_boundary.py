"""Batch 208 (C7) — module_extractor AI boundary suggestions tests."""
from __future__ import annotations

import pytest

from app.services import ai_client
from app.services.ai_client import AiClientUnavailableError
from app.services.knowledge.module_extractor import ai_boundary_suggestions_sync


def test_ai_boundary_suggestions_configured(monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: True)
    monkeypatch.setattr(
        ai_client,
        "chat_completions",
        lambda *a, **k: {
            "suggestions": [
                {"folder": "会员中心", "merge_into": "会员", "reason": "同域"}
            ]
        },
    )
    out = ai_boundary_suggestions_sync(
        None, 1, [("会员中心", 3), ("订单", 2)]
    )
    assert out == [
        {"folder": "会员中心", "merge_into": "会员", "reason": "同域"}
    ]


def test_ai_boundary_suggestions_unconfigured_returns_empty(monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: False)
    assert ai_boundary_suggestions_sync(None, 1, [("x", 1)]) == []


def test_ai_boundary_suggestions_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: True)

    def _boom(*a, **k):
        raise AiClientUnavailableError("down")

    monkeypatch.setattr(ai_client, "chat_completions", _boom)
    assert ai_boundary_suggestions_sync(None, 1, [("x", 1)]) == []


def test_ai_boundary_suggestions_invalid_payload_returns_empty(monkeypatch):
    monkeypatch.setattr(ai_client, "is_configured", lambda db2, pid: True)
    monkeypatch.setattr(
        ai_client, "chat_completions", lambda *a, **k: {"nope": []}
    )
    assert ai_boundary_suggestions_sync(None, 1, [("x", 1)]) == []
