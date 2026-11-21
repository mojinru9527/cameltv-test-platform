"""V16-003：API 输出遮蔽（Run/Node/Assertion/Artifact detail 永不明文返回 Secret）。

规则：
- Secret Handle 引用 → 只返回不可逆句柄元信息（``secret://<id>``），不返回明文；
- 字段名命中敏感规则且值不是脱敏占位 → ``***``；
- 字符串命中 JWT/Bearer/API key/私钥/canary 值模式 → ``***``；
- 其余字段原样返回。
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.aiqe.redaction import CLASSIFIER, REDACTED, is_secret_handle_reference

SECRET_SCHEME = "secret://"


def mask_handle_reference(value: Mapping[str, Any]) -> dict[str, Any]:
    handle_id = str(value.get("secret_handle_id") or "")
    return {
        "secret_handle_id": handle_id,
        "secret_ref": f"{SECRET_SCHEME}{handle_id}",
        "key_name": value.get("key_name"),
        "secret_type": value.get("secret_type"),
        "expires_at": value.get("expires_at"),
        "masked": True,
    }


def mask_for_api(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return REDACTED
    if is_secret_handle_reference(value):
        return mask_handle_reference(value)  # type: ignore[arg-type]
    if isinstance(value, Mapping):
        masked: dict[str, Any] = {}
        for key, item in list(value.items())[:500]:
            if is_secret_handle_reference(item):
                masked[str(key)] = mask_handle_reference(item)  # type: ignore[arg-type]
                continue
            if CLASSIFIER.is_sensitive_key(key) and item not in (None, "", REDACTED):
                masked[str(key)] = REDACTED
                continue
            masked[str(key)] = mask_for_api(item, depth=depth + 1)
        return masked
    if isinstance(value, (list, tuple)):
        return [mask_for_api(item, depth=depth + 1) for item in value[:500]]
    if isinstance(value, str):
        if CLASSIFIER.find_secrets(value):
            return REDACTED
        return value
    return value


__all__ = ["SECRET_SCHEME", "mask_for_api", "mask_handle_reference"]
