"""AI 提供方错误归因与健康态登记（V4.0 生产黑盒复盘 P0-2 / P1-4 / P2-6 / P2-7）。

背景缺陷：
  * 生产 DeepSeek Key 返回 401 时，`ai_service` 把传输/鉴权失败一律包装成
    「AI 返回的 JSON 格式异常，无法解析…请检查该文件中的 JSON 语法错误」，
    归因完全错误，并把服务器临时文件路径 `/tmp/ai_response_failed_*.json`
    暴露给终端用户（用户无法访问该路径）。
  * `ai_config_service.test_connection` 把原始异常串
    （`HTTPStatusError: Client error '401 ...' ... https://developer.mozilla.org/...`）
    直接回给前端 toast。
  * `/api/v1/ai-config/resolve` 的 `configured` 只表示「填过 Key」，不表示「Key 可用」，
    因此 Key 失效时 AI 配置页/DSH 页/需求页仍统一显示「已配置 / 可用」。

本模块提供：
  1. `classify_ai_error` / `humanize_ai_error`：把底层异常或错误串归一成
     可执行的中文提示（与 DSH 模块既有文案对齐）。
  2. 进程内 `AiHealthRegistry`：AI 调用点被动登记成功/失败，`resolve_out`
     据此对外暴露真实健康态，供前端在入口处前置提示。
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

# ── 错误分类 ──

UNAUTHORIZED = "unauthorized"
FORBIDDEN = "forbidden"
QUOTA = "quota"
RATE_LIMITED = "rate_limited"
NOT_FOUND = "not_found"
TIMEOUT = "timeout"
UNREACHABLE = "unreachable"
BAD_RESPONSE = "bad_response"
UNCONFIGURED = "unconfigured"
UNKNOWN = "unknown"

_STATUS_RE = re.compile(r"\b(40[0-9]|41[0-9]|42[0-9]|50[0-9])\b")


def _status_of(text: str) -> int | None:
    m = _STATUS_RE.search(text or "")
    return int(m.group(1)) if m else None


def classify_ai_error(error: BaseException | str | None) -> str:
    """把异常或错误串归一为稳定的错误类别常量。"""
    if error is None:
        return UNKNOWN
    text = str(error)
    lowered = text.lower()

    # 注意用 lowered 比对：原文是「未配置 AI 提供方」（大写 AI），
    # 用未小写的 text 去匹配小写字面量会永远不命中。
    if "未配置 ai 提供方" in lowered or "ai 配置密钥已失效" in lowered:
        return UNCONFIGURED

    status = _status_of(text)
    if status == 401 or "unauthorized" in lowered or "invalid api key" in lowered:
        return UNAUTHORIZED
    if status == 403 or "forbidden" in lowered:
        return FORBIDDEN
    if status == 402 or "insufficient" in lowered or "balance" in lowered or "quota" in lowered:
        return QUOTA
    if status == 429 or "rate limit" in lowered or "too many requests" in lowered:
        return RATE_LIMITED
    if status == 404 or "model not exist" in lowered or "not found" in lowered:
        return NOT_FOUND
    if "timeout" in lowered or "timed out" in lowered:
        return TIMEOUT
    if (
        "connecterror" in lowered
        or "connection" in lowered
        or "name or service not known" in lowered
        or "getaddrinfo" in lowered
        or "ssl" in lowered
    ):
        return UNREACHABLE
    if "jsondecodeerror" in lowered or "json" in lowered:
        return BAD_RESPONSE
    return UNKNOWN


_MESSAGES: dict[str, str] = {
    UNAUTHORIZED: "AI 提供方 API Key 无效或已过期（401）——请到「AI 配置」更新密钥",
    FORBIDDEN: "AI 提供方拒绝访问（403）——请确认该 Key 是否有调用该模型的权限",
    QUOTA: "AI 提供方余额或配额不足——请到提供方控制台充值后重试",
    RATE_LIMITED: "AI 提供方触发限流（429）——请稍后重试或降低并发",
    NOT_FOUND: "AI 提供方未找到该模型或接口——请到「AI 配置」核对模型名与 API 地址",
    TIMEOUT: "调用 AI 提供方超时——请检查网络或稍后重试",
    UNREACHABLE: "无法连接 AI 提供方——请检查 API 地址与服务器出网策略",
    BAD_RESPONSE: "AI 返回内容无法解析为 JSON——已记录原始响应，请重试或更换模型",
    UNCONFIGURED: "当前项目未配置可用的 AI 提供方——请在「AI 配置」中添加",
    UNKNOWN: "AI 调用失败",
}


def humanize_ai_error(
    error: BaseException | str | None,
    provider_name: str = "",
    *,
    include_detail: bool = False,
) -> str:
    """返回面向用户的中文提示。

    `include_detail=True` 时附加一行原始错误摘要（供任务详情页展开排查），
    但**始终不包含**服务器本地文件路径。
    """
    kind = classify_ai_error(error)
    msg = _MESSAGES.get(kind, _MESSAGES[UNKNOWN])
    if provider_name:
        msg = f"{msg}（提供方：{provider_name}）"
    if include_detail and error is not None:
        detail = _strip_local_paths(str(error)).strip()
        if detail:
            msg = f"{msg}\n原始错误：{detail[:300]}"
    return msg


_URL_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s'\"<>]+")
# 仅匹配**本地文件系统**路径：Windows 盘符路径，或以常见系统根目录开头的绝对路径。
# 不使用「任意 /a/b/c」这类宽松写法——那会把 URL 的 path 一并吃掉，
# 反而抹去排查所需的端点信息（本地验证实测 https://api.deepseek.com/... 被误脱敏）。
_LOCAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\[^\s'\"<>|*?]+"
    r"|/(?:tmp|var|home|root|app|opt|usr|srv|data|mnt|Users)(?:/[^\s'\"<>]+)*)"
)


def _strip_local_paths(text: str) -> str:
    """移除服务器本地路径，避免把 /tmp/... 之类内部信息透给终端用户。

    URL 先占位保护再还原——端点地址对用户排查有价值，且不属于内部路径泄露。
    """
    if not text:
        return ""
    urls: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        urls.append(m.group(0))
        return f"\x00URL{len(urls) - 1}\x00"

    protected = _URL_RE.sub(_stash, text)
    cleaned = _LOCAL_PATH_RE.sub("<服务端日志>", protected)
    for i, url in enumerate(urls):
        cleaned = cleaned.replace(f"\x00URL{i}\x00", url)
    return cleaned


# ── 健康态登记 ──


@dataclass(frozen=True)
class AiHealth:
    status: str  # "ok" | "error" | "unknown"
    kind: str
    message: str
    provider_id: int | None
    checked_at: str | None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "kind": self.kind,
            "message": self.message,
            "provider_id": self.provider_id,
            "checked_at": self.checked_at,
        }


UNKNOWN_HEALTH = AiHealth("unknown", "", "", None, None)


class AiHealthRegistry:
    """进程内最近一次 AI 调用结果（按项目）。

    刻意不落库：这是"最近一次真实调用"的观测值，进程重启后回到 unknown，
    UI 以 unknown 表示"尚未验证"，不会把陈旧状态当成事实。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_project: dict[int, AiHealth] = {}

    def record_success(self, project_id: int, provider_id: int | None = None) -> None:
        with self._lock:
            self._by_project[project_id] = AiHealth(
                "ok", "", "", provider_id, _now()
            )

    def record_failure(
        self,
        project_id: int,
        error: BaseException | str | None,
        provider_id: int | None = None,
        provider_name: str = "",
    ) -> AiHealth:
        health = AiHealth(
            "error",
            classify_ai_error(error),
            humanize_ai_error(error, provider_name),
            provider_id,
            _now(),
        )
        with self._lock:
            self._by_project[project_id] = health
        return health

    def get(self, project_id: int) -> AiHealth:
        with self._lock:
            return self._by_project.get(project_id, UNKNOWN_HEALTH)

    def reset(self) -> None:
        with self._lock:
            self._by_project.clear()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


ai_health_registry = AiHealthRegistry()
