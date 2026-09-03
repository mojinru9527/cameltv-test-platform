from __future__ import annotations

import pytest

from app.services import ai_client, version_task_ai_service


def test_build_user_message_includes_imported_openapi_contract():
    message = version_task_ai_service._build_user_message(
        {
            "title": "体育 16.0.0",
            "version": "16.0.0",
            "scope": {
                "modules": ["篮球", "足球"],
                "openapi_endpoints": [
                    {"method": "GET", "path": "/box-score", "summary": "篮球 Box Score"}
                ],
            },
        }
    )

    assert "GET /box-score" in message
    assert "篮球 Box Score" in message


def test_call_llm_retries_empty_content(monkeypatch):
    responses = iter([
        {"content": "", "finish_reason": "stop", "truncated": False},
        {
            "content": '{"items":[{"item_type":"functional","title":"篮球 Box Score"}]}',
            "finish_reason": "stop",
            "truncated": False,
        },
    ])
    monkeypatch.setattr(ai_client, "chat_completions_full", lambda *_args, **_kwargs: next(responses))

    result = version_task_ai_service._call_llm_sync(None, 1, "system", "user")

    assert result[0]["title"] == "篮球 Box Score"


def test_call_llm_rejects_repeated_invalid_content(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "chat_completions_full",
        lambda *_args, **_kwargs: {"content": "not-json", "finish_reason": "stop", "truncated": False},
    )

    with pytest.raises(ai_client.AiClientResponseError, match="无法解析"):
        version_task_ai_service._call_llm_sync(None, 1, "system", "user")
