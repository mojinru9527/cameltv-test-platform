from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.models.notification import NotificationChannel, NotificationLog
from app.services import notify_service


def test_lifecycle_templates_contain_required_task_fields():
    payload = notify_service._format_msg(
        "task_finished",
        {
            "task_type": "API 测试",
            "task_name": "测试5账号查询",
            "status": "success",
            "result_summary": "通过 3 / 失败 0",
            "link": "http://localhost:5173/apitest",
        },
        "generic",
    )

    assert payload["text"].startswith("## 测试任务已结束")
    assert "测试5账号查询" in payload["text"]
    assert "通过 3 / 失败 0" in payload["text"]


def test_missing_optional_template_fields_do_not_crash():
    payload = notify_service._format_msg(
        "task_started", {"task_name": "最小任务"}, "generic",
    )
    assert "最小任务" in payload["text"]
    assert "**类型**: -" in payload["text"]


def test_dingtalk_lifecycle_payload_uses_markdown_robot_schema():
    """DingTalk custom robots require the msgtype/markdown payload shape."""
    payload = notify_service._format_msg(
        "task_started",
        {
            "task_type": "API",
            "task_name": "Test5 query",
            "triggered_by": "DEV",
            "link": "http://localhost:5173/apitest",
        },
        "dingtalk",
    )

    assert payload["msgtype"] == "markdown"
    assert payload["markdown"]["title"]
    assert "Test5 query" in payload["markdown"]["text"]


def test_subscribed_lifecycle_event_is_delivered_and_logged(db_session, monkeypatch):
    channel = NotificationChannel(
        project_id=1,
        name="DEV 本地接收器",
        channel_type="webhook",
        provider="generic",
        webhook_url="http://127.0.0.1:19999/webhook",
        events='["task_started", "task_finished", "test_result"]',
        enabled=True,
    )
    db_session.add(channel)
    db_session.commit()

    captured = []

    async def fake_send(url, payload, retries=2):
        captured.append((url, payload))
        return True, "", 1

    monkeypatch.setattr(notify_service, "_send_webhook", fake_send)
    result = asyncio.run(notify_service.notify(
        db_session,
        1,
        "test_result",
        {
            "task_name": "音视频首帧",
            "passed": 12,
            "failed": 0,
            "skipped": 0,
            "pass_rate": "100%",
            "conclusion": "通过",
            "link": "http://localhost:5173/special",
        },
    ))

    assert result == {"sent": 1, "failed": 0, "skipped": 0}
    assert captured and "音视频首帧" in captured[0][1]["text"]
    log = db_session.scalar(select(NotificationLog))
    assert log is not None
    assert log.event == "test_result"
    assert log.status == "sent"
