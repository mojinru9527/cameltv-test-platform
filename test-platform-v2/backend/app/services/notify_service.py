"""Notification service — dispatch events to configured webhook channels.

Events: plan_done, defect_assigned, schedule_failed, report_generated.
Channels: webhook (feishu/dingtalk/wecom_work/generic).

Usage:
    import asyncio
    from app.services.notify_service import notify

    asyncio.create_task(notify(db, project_id, "plan_done", {...}))
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import ssl
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import NotificationChannel

logger = logging.getLogger("notify")

# ── Message templates (markdown) ──────────────────────

_TEMPLATES: dict[str, str] = {
    "plan_done": (
        "## 测试计划执行完成\n"
        "**计划**: {plan_name}\n"
        "**结果**: {result_summary}\n"
        "**时间**: {time}\n"
        "[查看详情]({link})"
    ),
    "defect_assigned": (
        "## 缺陷指派通知\n"
        "**缺陷**: [{severity}] {title}\n"
        "**指派给**: {assignee}\n"
        "**状态**: {status}\n"
        "[查看详情]({link})"
    ),
    "schedule_failed": (
        "## 定时任务执行失败\n"
        "**任务**: {schedule_name}\n"
        "**错误**: {error}\n"
        "**时间**: {time}\n"
        "[查看详情]({link})"
    ),
    "report_generated": (
        "## 测试报告已生成\n"
        "**报告**: {report_name}\n"
        "**通过率**: {pass_rate}\n"
        "**时间**: {time}\n"
        "[查看详情]({link})"
    ),
    "case_reviewed": (
        "## 用例评审通知\n"
        "**用例**: {case_title}\n"
        "**操作**: {action}\n"
        "**评审人**: {reviewer}\n"
        "**意见**: {comment}\n"
        "**时间**: {time}\n"
        "[查看详情]({link})"
    ),
}


# ── P1-C2: ThreadPoolExecutor module singleton ─────────

_notify_executor: concurrent.futures.ThreadPoolExecutor | None = None


def _get_notify_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Return the module-level ThreadPoolExecutor singleton for notifications."""
    global _notify_executor
    if _notify_executor is None:
        _notify_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    return _notify_executor


def _format_msg(event: str, data: dict, provider: str) -> dict | str:
    """Format a message payload for the target provider."""
    template = _TEMPLATES.get(event, "")
    time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = template.format(time=time_str, **data)

    if provider == "feishu":
        return {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": data.get("title", "通知"), "tag": "plain_text"}},
                "elements": [{"tag": "markdown", "content": text}],
            },
        }
    elif provider == "dingtalk":
        return {"msgtype": "markdown", "markdown": {"title": "通知", "text": text}}
    elif provider == "wecom_work":
        return {"msgtype": "markdown", "markdown": {"content": text}}
    else:
        # generic — plain markdown in text field
        return {"text": text}


async def _send_webhook(url: str, payload: dict | str, retries: int = 2) -> tuple[bool, str, int]:
    """Send a webhook notification with retry (best-effort).

    Returns (success, last_error, attempt_count).
    """
    last_error = ""
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if isinstance(payload, dict):
                    resp = await client.post(url, json=payload)
                else:
                    resp = await client.post(url, content=payload)
                if resp.status_code < 400:
                    return True, "", attempt + 1
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            last_error = str(e)[:200]
        if attempt < retries:
            await asyncio.sleep(1.0 * (attempt + 1))  # linear backoff
    logger.warning(f"Webhook {url[:50]}... failed after {retries + 1} attempts: {last_error}")
    return False, last_error, retries + 1


async def _send_email(
    to_addrs: list[str], subject: str, body: str,
    smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, smtp_from: str,
) -> bool:
    """Send email via SMTP (best-effort)."""
    import smtplib
    from email.mime.text import MIMEText

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = ", ".join(to_addrs)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _sync_send_email(smtp_host, smtp_port, smtp_user, smtp_password, msg),
        )
        return True
    except Exception as e:
        logger.warning(f"SMTP send failed: {e}")
        return False


def _sync_send_email(host, port, user, password, msg):
    """Send email via SMTP with TLS certificate validation (P1-S5a).

    Certificate verification is controlled by settings.smtp_verify_cert.
    When disabled, a security warning is logged.
    On certificate verification failure, the error is logged and the
    exception is re-raised (no silent downgrade).
    """
    import smtplib
    from app.core.config import settings

    # P1-S5a: Build SSL context with optional CA bundle
    ssl_context = ssl.create_default_context()
    if not settings.smtp_verify_cert:
        logger.warning("SMTP 证书验证已关闭，邮件传输不安全")
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    if settings.smtp_ca_bundle:
        ssl_context.load_verify_locations(settings.smtp_ca_bundle)

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls(context=ssl_context)
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    except ssl.SSLError as e:
        logger.error("SMTP TLS 证书验证失败: host=%s port=%s error=%s", host, port, e)
        raise


async def notify(db: Session, project_id: int, event: str, data: dict) -> dict:
    """Dispatch an event notification to all matching channels (fire-and-forget).

    Records send logs for each attempt. Returns a summary dict.
    """
    from app.models.notification import NotificationLog

    channels = db.scalars(
        select(NotificationChannel).where(
            NotificationChannel.project_id == project_id,
            NotificationChannel.enabled == True,
        )
    ).all()

    results = {"sent": 0, "failed": 0, "skipped": 0}
    for ch in channels:
        try:
            evts = json.loads(ch.events or "[]")
        except json.JSONDecodeError:
            evts = []
        if event not in evts:
            results["skipped"] += 1
            continue

        # ── Route by channel type ──
        if ch.channel_type == "email":
            ok, last_error, attempts = await _dispatch_email(event, data, ch)
        else:
            ok, last_error, attempts = await _dispatch_webhook(event, data, ch)

        # P1-4/S4b: 记录实际错误详情（不再使用 "Delivery failed" 硬编码）
        log = NotificationLog(
            channel_id=ch.id, project_id=project_id, event=event,
            status="sent" if ok else "failed",
            error="" if ok else last_error,
            retry_count=0 if ok else attempts,
        )
        db.add(log)
        try:
            db.commit()
        except Exception:
            db.rollback()

        if ok:
            results["sent"] += 1
        else:
            results["failed"] += 1

    return results


async def _dispatch_webhook(event: str, data: dict, ch) -> tuple[bool, str, int]:
    """Send event via webhook channel. Returns (success, last_error, attempts)."""
    payload = _format_msg(event, data, ch.provider)
    return await _send_webhook(ch.webhook_url, payload)


async def _dispatch_email(event: str, data: dict, ch) -> tuple[bool, str, int]:
    """Send event via email channel using global SMTP config.
    Returns (success, last_error, attempts).
    """
    from app.core.config import settings

    if not settings.smtp_host:
        logger.warning("SMTP not configured, skipping email notification")
        return False, "SMTP not configured", 0

    recipients = [addr.strip() for addr in ch.webhook_url.split(",") if addr.strip()]
    if not recipients:
        return False, "No recipients configured", 0

    subject_map = {
        "plan_done": f"测试计划执行完成 — {data.get('plan_name', '')}",
        "defect_assigned": f"[{data.get('severity', '')}] 缺陷指派 — {data.get('title', '')}",
        "schedule_failed": f"定时任务失败 — {data.get('schedule_name', '')}",
        "report_generated": f"测试报告已生成 — {data.get('report_name', '')}",
        "case_reviewed": f"用例评审通知 — {data.get('case_title', '')}",
    }
    subject = subject_map.get(event, f"通知: {event}")

    template = _TEMPLATES.get(event, "")
    time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = template.format(time=time_str, **data)

    ok = await _send_email(
        to_addrs=recipients,
        subject=subject,
        body=body,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        smtp_from=settings.smtp_from or settings.smtp_user,
    )
    return (ok, "SMTP send failed" if not ok else "", 1)


# ── Sync helpers for use in BackgroundTasks / sync callers ─────

def notify_sync(db: Session, project_id: int, event: str, data: dict) -> dict:
    """Synchronous wrapper — runs notify() to completion.

    P1-4/S4c: 移除 asyncio.get_event_loop() 探测逻辑。
    - 在 BackgroundTasks 线程中调用时（无事件循环）→ asyncio.run()
    - 在已有事件循环的上下文中 → 通过 run_in_executor 避免嵌套

    Prefer BackgroundTasks + _run_notify_in_new_session for fire-and-forget use cases.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop in this thread (e.g., BackgroundTasks thread pool)
        return asyncio.run(notify(db, project_id, event, data))

    # Event loop is running — delegate to a separate thread to avoid nesting
    # P1-C2: Use module-level executor singleton instead of creating a new pool each time
    pool = _get_notify_executor()
    future = pool.submit(asyncio.run, notify(db, project_id, event, data))
    return future.result()


# ── Channel CRUD ──────────────────────────────────────

def list_channels(db: Session, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(NotificationChannel).where(NotificationChannel.project_id == project_id)
    ).all()
    return [_ch_to_dict(r) for r in rows]


def create_channel(db: Session, data, project_id: int) -> dict:
    ch = NotificationChannel(
        project_id=project_id,
        name=data.get("name", ""),
        channel_type=data.get("channel_type", "webhook"),
        provider=data.get("provider", "generic"),
        webhook_url=data.get("webhook_url", ""),
        events=json.dumps(data.get("events", []), ensure_ascii=False),
        enabled=data.get("enabled", True),
    )
    db.add(ch)
    db.flush()
    return _ch_to_dict(ch)


def update_channel(db: Session, ch_id: int, data, project_id: int) -> dict | None:
    ch = db.scalar(
        select(NotificationChannel).where(
            NotificationChannel.id == ch_id,
            NotificationChannel.project_id == project_id,
        )
    )
    if not ch:
        return None
    for k in ("name", "channel_type", "provider", "webhook_url", "enabled"):
        if k in data and data[k] is not None:
            setattr(ch, k, data[k])
    if "events" in data and data["events"] is not None:
        ch.events = json.dumps(data["events"], ensure_ascii=False)
    db.flush()
    return _ch_to_dict(ch)


def delete_channel(db: Session, ch_id: int, project_id: int) -> bool:
    ch = db.scalar(
        select(NotificationChannel).where(
            NotificationChannel.id == ch_id,
            NotificationChannel.project_id == project_id,
        )
    )
    if not ch:
        return False
    db.delete(ch)
    db.flush()
    return True


def _ch_to_dict(ch: NotificationChannel) -> dict:
    try:
        events = json.loads(ch.events or "[]")
    except json.JSONDecodeError:
        events = []
    return {
        "id": ch.id, "project_id": ch.project_id,
        "name": ch.name, "channel_type": ch.channel_type,
        "provider": ch.provider, "webhook_url": ch.webhook_url,
        "enabled": ch.enabled, "events": events,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
    }
