"""AUD-003：共享敏感数据分类器与证据脱敏器。

单一实现（禁止每个 Driver 各写一套），覆盖 v1.5 §01 AUD-003「敏感分类」：

- **字段名规则**：password/passwd/secret/token/access_token/refresh_token/id_token/
  authorization/cookie/set-cookie/api_key/private_key/client_secret/signing_key/session/
  otp/phone/email/id_card；
- **值模式**：JWT、OAuth Bearer、PEM 私钥、云访问密钥（AKIA…）、``sk-…``、
  ``key=value`` 形式的 token/secret、以及测试用 canary（``CANARY_SECRET_*``）；
- **fail closed**：对未识别字段但命中高风险值模式的字符串一律替换为 ``***``，
  并可由调用方升级为 ``SENSITIVE_OUTPUT_BLOCKED``。

所有持久化（NodeRun.output_ref / StepAttempt / RunEvent / Artifact / LLM Prompt）
必须先经过这里。
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

REDACTED = "***"
MAX_DEPTH = 8
MAX_ITEMS = 500
MAX_TEXT = 256 * 1024

#: 字段名规则（大小写不敏感，允许 - / _ / 驼峰前缀）。
SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[_\-. ])(?:"
    r"password|passwd|pwd|secret|token|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"auth(?:orization)?|cookie|set[_-]?cookie|api[_-]?key|apikey|private[_-]?key|"
    r"client[_-]?secret|signing[_-]?key|session(?:[_-]?id)?|otp|"
    r"phone|mobile|email|id[_-]?card|bank[_-]?card"
    r")(?:$|[_\-. ])",
    re.IGNORECASE,
)
#: 兼容无分隔符的驼峰/整词字段（accessToken、Authorization、cookie）。
SENSITIVE_KEY_LOOSE_RE = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|apikey|api_key|private_key|"
    r"client_secret|signing_key|session|otp|phone|email|id_card)",
    re.IGNORECASE,
)

#: 高置信值模式；命中即视为 secret（无论字段名叫什么）。
SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{4,}"),  # JWT
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-~+/=]{8,}"),
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]{16,}?-----END [A-Z0-9 ]*PRIVATE KEY-----"
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),  # OpenAI 风格 key
    re.compile(
        r"(?i)\b(?:access[_-]?token|refresh[_-]?token|id[_-]?token|api[_-]?key|secret|"
        r"password|client[_-]?secret)\b\s*[=:]\s*[\"']?([A-Za-z0-9._\-+/=]{12,})"
    ),
    re.compile(r"\bCANARY_SECRET_[A-Za-z0-9_\-]+"),  # 测试 canary（AUD-003 §9）
)
#: ``"access_token": "value"`` 这类 JSON 文本（非结构解析路径的兜底）。
JSON_PAIR_RE = re.compile(
    r'(?P<key>"(?:[^"\\]|\\.)*")\s*:\s*(?P<value>"(?:[^"\\]|\\.)*"|[-+]?\d+(?:\.\d+)?|true|false|null)',
    re.IGNORECASE,
)


class SecretLeakError(ValueError):
    """检测到疑似 secret 明文，调用方必须阻断持久化/外发。"""


#: V16-003：合法的 Secret Handle 引用结构（不含明文），脱敏与断言必须放行。
HANDLE_ID_KEY = "secret_handle_id"
HANDLE_REF_KEY = "secret_ref"


def is_secret_handle_reference(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    handle_id = value.get(HANDLE_ID_KEY)
    if not isinstance(handle_id, str) or not handle_id:
        return False
    ref = str(value.get(HANDLE_REF_KEY) or "")
    return ref.startswith("vault://") or ref.startswith("secret://")


def normalize_key(key: Any) -> str:
    return str(key if key is not None else "").strip()


class SensitiveDataClassifier:
    """字段名 + 值模式双重判定；不依赖外部配置。"""
    def is_sensitive_key(self, key: Any) -> bool:
        text = normalize_key(key)
        if not text:
            return False
        if SENSITIVE_KEY_RE.search(text):
            return True
        # 驼峰/无分隔符：authToken、accessToken、X-Auth-Token
        return bool(SENSITIVE_KEY_LOOSE_RE.search(text))

    def find_secrets(self, text: str) -> list[str]:
        if not isinstance(text, str) or not text:
            return []
        found: list[str] = []
        for pattern in SECRET_VALUE_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(1) if match.groups() else match.group(0)
                if value and value != REDACTED:
                    found.append(value)
        return found

    def contains_secret(self, text: str) -> bool:
        return bool(self.find_secrets(text))


CLASSIFIER = SensitiveDataClassifier()


class Redactor:
    """递归脱敏：字段名命中 → 整值替换；值命中高风险模式 → 文本替换。"""

    def __init__(self, classifier: SensitiveDataClassifier | None = None) -> None:
        self.classifier = classifier or CLASSIFIER

    def redact(self, value: Any, *, key: Any = None, depth: int = 0) -> Any:
        if depth > MAX_DEPTH:
            return REDACTED
        if is_secret_handle_reference(value):
            # Handle 引用是脱敏后的安全表示，绝不能把 id/ref 替换成 ***（否则下游无法解析）。
            return dict(value)
        if key is not None and self.classifier.is_sensitive_key(key):
            # 字段名命中即整值替换（含嵌套对象），空值保持空值便于断言「存在性」。
            return REDACTED if value not in (None, "") else value
        if isinstance(value, Mapping):
            items = list(value.items())[:MAX_ITEMS]
            return {
                str(item_key): self.redact(item_value, key=item_key, depth=depth + 1)
                for item_key, item_value in items
            }
        if isinstance(value, (list, tuple)):
            return [self.redact(item, depth=depth + 1) for item in value[:MAX_ITEMS]]
        if isinstance(value, str):
            return self.redact_text(value)
        return value

    def redact_text(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text
        candidate = text[:MAX_TEXT]
        stripped = candidate.strip()
        if stripped[:1] in "{[":
            try:
                parsed = json.loads(stripped)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, (dict, list)):
                redacted = self.redact(parsed)
                suffix = text[MAX_TEXT:]
                return json.dumps(redacted, ensure_ascii=False) + suffix

        result = candidate
        for pattern in SECRET_VALUE_PATTERNS:
            result = pattern.sub(REDACTED, result)

        def _pair(match: re.Match[str]) -> str:
            raw_key = match.group("key")
            try:
                key_name = json.loads(raw_key)
            except (ValueError, TypeError):
                key_name = raw_key
            if self.classifier.is_sensitive_key(key_name):
                return f"{raw_key}: {json.dumps(REDACTED)}"
            redacted_value = self.redact_text(match.group("value"))
            return f"{raw_key}: {redacted_value}"

        result = JSON_PAIR_RE.sub(_pair, result)
        return result + text[MAX_TEXT:]

    def assert_clean(self, value: Any, *, where: str = "") -> None:
        """持久化/外发前的最后一道断言；命中即抛 ``SecretLeakError``。"""
        leaks = self._collect_leaks(value)
        if leaks:
            raise SecretLeakError(f"{where or 'value'} 含疑似 secret 明文: {leaks[:3]}")

    def _collect_leaks(self, value: Any, *, depth: int = 0) -> list[str]:
        if depth > MAX_DEPTH:
            return []
        if isinstance(value, Mapping):
            if is_secret_handle_reference(value):
                return []
            leaks: list[str] = []
            for item_key, item_value in _safe_items(value):
                if self.classifier.is_sensitive_key(item_key) and item_value not in (
                    None,
                    "",
                    REDACTED,
                ):
                    if isinstance(item_value, str) and item_value.startswith("vault://"):
                        continue
                    leaks.append(str(item_key))
                    continue
                leaks.extend(self._collect_leaks(item_value, depth=depth + 1))
            return leaks
        if isinstance(value, (list, tuple)):
            leaks = []
            for item in value[:MAX_ITEMS]:
                leaks.extend(self._collect_leaks(item, depth=depth + 1))
            return leaks
        if isinstance(value, str):
            return self.classifier.find_secrets(value)
        return []


def _safe_items(value: Any) -> list[tuple[Any, Any]]:
    try:
        return list(value.items())[:MAX_ITEMS]
    except Exception:  # pragma: no cover - 防御异常 Mapping
        return []


DEFAULT_REDACTOR = Redactor()


def redact_mapping(value: Any, *, where: str = "") -> Any:
    """模块级便捷入口：任何待持久化的 payload 都应先过这里。"""
    return DEFAULT_REDACTOR.redact(value)


def redact_text(text: str) -> str:
    return DEFAULT_REDACTOR.redact_text(text)


def assert_no_secret(value: Any, *, where: str = "") -> None:
    DEFAULT_REDACTOR.assert_clean(value, where=where)


def contains_secret(value: Any) -> bool:
    return bool(DEFAULT_REDACTOR._collect_leaks(value))


__all__ = [
    "CLASSIFIER",
    "DEFAULT_REDACTOR",
    "REDACTED",
    "SECRET_VALUE_PATTERNS",
    "SENSITIVE_KEY_RE",
    "Redactor",
    "SecretLeakError",
    "SensitiveDataClassifier",
    "assert_no_secret",
    "contains_secret",
    "redact_mapping",
    "redact_text",
]
