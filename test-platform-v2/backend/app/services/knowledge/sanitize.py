"""知识入库脱敏 —— 敏感字段进入知识库前统一遮蔽（文档 §17.2）。

规则：
- Authorization / Cookie / Bearer / X-Api-Token 等鉴权头（行首或行内） → 遮蔽 value
- 裸 JWT（`eyJ....`，无论有无 Bearer 前缀） → 整体遮蔽
- JSON / 对象字面量中的 password/secret/token/api_key 等键值（单双引号 + 无引号值） → 遮蔽 value
- 查询串 / 表单 `token=xxx`、日志/YAML 风格 `token: xxx` → 遮蔽 value
- 手机号（连续或带 `-`/空格/`.` 分隔） / 邮箱 / 身份证 → 部分遮蔽

设计为「尽力而为、宁可多遮蔽」：绝不让密钥/令牌/PII 明文进库。所有正则均大小写不敏感。
为避免误伤中文正文，无引号形态仅遮蔽「以 ASCII 字母数字开头且形似密钥」的值。
"""
from __future__ import annotations

import re

MASK = "***"

# 敏感键名（token/密钥/凭据类），供多条规则复用
_SECRET_KEYS = (
    r"password|passwd|pwd|secret|token|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"api[_-]?key|apikey|app[_-]?key|app[_-]?secret|authorization|cookie|set-cookie|"
    r"session(?:[_-]?id)?|credential|private[_-]?key|sign(?:ature)?|sig"
)
# 无引号「形似密钥」的值：ASCII 字母数字起头，仅 ASCII 令牌字符（不吞中文正文），≥2 字符
_SECRET_VALUE = r"[A-Za-z0-9][A-Za-z0-9._\-+/=]{1,}"

# 1) 裸 JWT：header.payload.signature（base64url，signature 可空）——最前，优先整体遮蔽
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]*")

# 2) 鉴权头：Authorization/Cookie/X-Api-Key 等（行首或行内均可，遮蔽到行尾）
_HEADER_RE = re.compile(
    r"(?i)((?:authorization|proxy-authorization|cookie|set-cookie|"
    r"x-api-key|x-api-token|x-auth-token|x-access-token)\s*[:=]\s*)[^\r\n]+"
)

# 3) Bearer <token>（行内，独立出现）
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*")

# 4) JSON / 对象字面量：key: "value" 或 'key': 'value'（单双引号 key/value 均可）
_JSON_SECRET_RE = re.compile(
    r"(?i)([\"']?(?:" + _SECRET_KEYS + r")[\"']?\s*[:=]\s*)([\"'])(?:\\.|(?!\2).)*\2"
)
# 5) JSON 引号 key + 无引号值：{"api_key":998877} / {"token":true}
_JSON_SECRET_UNQUOTED_RE = re.compile(
    r"(?i)(\"(?:" + _SECRET_KEYS + r")\"\s*:\s*)(" + _SECRET_VALUE + r")"
)
# 6) 查询串 / 表单：token=xxx / ?access_token=xxx（无引号，值到分隔符止）
_KV_SECRET_RE = re.compile(
    r"(?i)\b((?:" + _SECRET_KEYS + r")=)[^\s&#\"'}<>]+"
)
# 7) 日志/YAML 风格：token: xxx / password: hunter2（无引号，形似密钥值）
_KV_COLON_SECRET_RE = re.compile(
    r"(?i)\b((?:" + _SECRET_KEYS + r")\s*:\s*)(" + _SECRET_VALUE + r")"
)

# 8) 中国大陆手机号（连续 11 位，或以 - / 空格 / . 分隔）
_PHONE_RE = re.compile(r"(?<![\d.\-])(1[3-9]\d)[\s.\-]?\d{4}[\s.\-]?(\d{4})(?![\d.\-])")

# 9) 邮箱（本地部/域名均加量词上界，避免长串上的 O(n²) 回溯 / ReDoS）
_EMAIL_RE = re.compile(
    r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]{0,63}"
    r"(@(?:[A-Za-z0-9-]{1,63}\.){1,8}[A-Za-z]{2,24})"
)

# 10) 身份证（18 位）
_IDCARD_RE = re.compile(r"(?<!\d)(\d{6})\d{8}(\d{3}[\dXx])(?!\d)")


def sanitize(text: str | None) -> str:
    """遮蔽文本中的敏感信息，返回可安全入库的字符串。"""
    if not text:
        return ""
    out = text
    out = _JWT_RE.sub(MASK, out)
    out = _HEADER_RE.sub(lambda m: m.group(1) + MASK, out)
    out = _BEARER_RE.sub("Bearer " + MASK, out)
    out = _JSON_SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + MASK + m.group(2), out)
    out = _JSON_SECRET_UNQUOTED_RE.sub(lambda m: m.group(1) + MASK, out)
    out = _KV_SECRET_RE.sub(lambda m: m.group(1) + MASK, out)
    out = _KV_COLON_SECRET_RE.sub(lambda m: m.group(1) + MASK, out)
    out = _PHONE_RE.sub(lambda m: m.group(1) + "****" + m.group(2), out)
    out = _EMAIL_RE.sub(lambda m: m.group(1) + MASK + m.group(2), out)
    out = _IDCARD_RE.sub(lambda m: m.group(1) + "********" + m.group(2), out)
    return out
