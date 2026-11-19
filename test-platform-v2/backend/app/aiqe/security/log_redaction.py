"""V16-003 §10：日志脱敏过滤器。

目标：任何通过标准 logging 输出的行（含异常堆栈）都不得包含 JWT/Bearer/API key/
私钥/canary 等敏感值。实现方式：

- 在格式化前重写 ``record.msg``/``record.args``；
- 预先格式化异常堆栈并写入 ``record.exc_text``（Formatter 会优先使用它）；
- 安装到 root handlers 与 ``app.aiqe`` logger。

注意：过滤器无法覆盖绕过 logging 的 ``print``/直接 stderr；生产要求统一走 logging。
"""
from __future__ import annotations

import contextvars
import logging

from app.aiqe.redaction import redact_text

#: 当前执行上下文已知的 secret 明文（动态 token/cookie 无法用正则识别，必须显式登记）。
_KNOWN_SECRETS: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
    "aiqe_known_secrets", default=()
)


def register_known_secrets(values) -> contextvars.Token:
    """登记本次执行已知的 secret 值；调用方必须在 finally 中 reset。"""
    cleaned = tuple(sorted({str(value) for value in values or () if str(value)}))
    return _KNOWN_SECRETS.set(cleaned)


def reset_known_secrets(token: contextvars.Token) -> None:
    try:
        _KNOWN_SECRETS.reset(token)
    except ValueError:  # pragma: no cover - 跨上下文 reset
        _KNOWN_SECRETS.set(())


def _scrub_known(text: str) -> str:
    scrubbed = redact_text(text)
    for value in _KNOWN_SECRETS.get():
        if value and value in scrubbed:
            scrubbed = scrubbed.replace(value, "***")
    return scrubbed


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - logging API
        try:
            message = record.getMessage()
            record.msg = _scrub_known(message)
            record.args = ()
        except Exception:  # pragma: no cover - 格式化失败不阻断日志
            pass
        try:
            if record.exc_info and not record.exc_text:
                formatter = logging.Formatter()
                record.exc_text = _scrub_known(formatter.formatException(record.exc_info))
        except Exception:  # pragma: no cover
            pass
        return True


_FILTER = SecretRedactingFilter()
_INSTALLED = False
_ORIGINAL_FACTORY = None


def _redacting_record_factory(*args, **kwargs):
    record = _ORIGINAL_FACTORY(*args, **kwargs)  # type: ignore[misc]
    try:
        message = record.getMessage()
        record.msg = _scrub_known(message)
        record.args = ()
    except Exception:  # pragma: no cover - 格式化失败不阻断日志
        pass
    return record


def install_log_redaction(*, logger_names: tuple[str, ...] = ("app", "app.aiqe")) -> None:
    """幂等安装：全局 LogRecord 工厂 + root handlers + 指定 logger。

    使用 ``logging.setLogRecordFactory`` 是唯一能覆盖 pytest caplog、
    uvicorn 等第三方 handler 的方式（logger/handler filter 都可能被绕过）。
    """
    global _INSTALLED, _ORIGINAL_FACTORY
    if _INSTALLED:
        return
    _ORIGINAL_FACTORY = logging.getLogRecordFactory()
    logging.setLogRecordFactory(_redacting_record_factory)
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(item, SecretRedactingFilter) for item in handler.filters):
            handler.addFilter(_FILTER)
    for name in logger_names:
        logger = logging.getLogger(name)
        if not any(isinstance(item, SecretRedactingFilter) for item in logger.filters):
            logger.addFilter(_FILTER)
    _INSTALLED = True


__all__ = ["SecretRedactingFilter", "install_log_redaction"]
