"""最小邮件发送服务（平台简化批次）。

通知配置模块已删除，但「忘记密码 → 重置邮件」是平台级认证能力，保留 env 级
SMTP 的最小发送函数（无配置页、无渠道/订阅体系）。SMTP 配置项沿用
``settings.smtp_*``（见 config.py），未配置时静默返回 False（防用户名枚举口径不变）。
"""
from __future__ import annotations

import logging
import ssl

logger = logging.getLogger("mail")


def _sync_send_email(host, port, user, password, msg):
    """Send email via SMTP with TLS certificate validation (P1-S5a).

    Certificate verification is controlled by settings.smtp_verify_cert.
    When disabled, a security warning is logged. On certificate verification
    failure, the error is logged and the exception is re-raised (no silent
    downgrade).
    """
    import smtplib
    from app.core.config import settings

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


def send_password_reset_email(to_addr: str, reset_url: str) -> bool:
    """Send a password-reset email without blocking the auth request.

    Returns False when the deployment has no complete SMTP/frontend link
    configuration or the user has no deliverable address.
    """
    from email.mime.text import MIMEText

    from app.core.config import settings

    if not (to_addr and reset_url and settings.smtp_host and (settings.smtp_from or settings.smtp_user)):
        return False

    body = (
        "你在 CamelTv 测试平台发起了密码重置。\n\n"
        f"请在 30 分钟内打开以下链接设置新密码：\n{reset_url}\n\n"
        "如果这不是你的操作，请忽略本邮件，现有密码不会改变。"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "CamelTv 测试平台 — 密码重置"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_addr

    import concurrent.futures

    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")
    _executor.submit(
        _sync_send_email,
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        msg,
    )
    return True
