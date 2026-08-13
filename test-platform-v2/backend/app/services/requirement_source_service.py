"""batch-167 Phase 1 — 需求 URL 适配器。

支持 generic HTML / PingCode / Confluence。外部凭据全部由 settings 环境变量注入，
缺失时 fail closed（明确错误，不伪造内容）。蓝湖链接仍走既有证据包质量门禁，
本服务只负责识别并给出引导。
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings

ALLOWED_SCHEMES = {"http", "https"}


class RequirementSourceError(ValueError):
    """需求源错误：分类后的用户可读错误。"""

    def __init__(self, message: str, kind: str = "general") -> None:
        super().__init__(message)
        self.kind = kind


class _TextHTMLParser(HTMLParser):
    """把 HTML 转为保留标题/列表层级的纯文本。"""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0
        self._block_tags = {"p", "div", "section", "article", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        if tag in self._block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript", "svg") and self._skip > 0:
            self._skip -= 1
        if tag in self._block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        raw = " ".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


def classify_url(url: str) -> str:
    """识别 URL 类型：lanhu / pingcode / confluence / generic。"""
    if not url or not url.strip():
        raise RequirementSourceError("需求地址为空", kind="input")
    host = (urlparse(url.strip()).hostname or "").lower()
    if not host:
        raise RequirementSourceError("需求地址不是合法的 URL", kind="input")
    if "lanhu" in host:
        return "lanhu"
    if "pingcode" in host:
        return "pingcode"
    if "atlassian" in host or "confluence" in host:
        return "confluence"
    return "generic"


def _request(url: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise RequirementSourceError(f"不支持的协议: {parsed.scheme}", kind="input")
    try:
        return httpx.get(
            url,
            headers=headers,
            timeout=settings.requirement_url_timeout_seconds,
            follow_redirects=True,
        )
    except httpx.TimeoutException as exc:  # must precede httpx.HTTPError (subclass)
        raise RequirementSourceError("需求地址请求超时，请检查网络或稍后重试", kind="timeout") from exc
    except httpx.HTTPError as exc:
        raise RequirementSourceError(f"需求地址请求失败: {exc}", kind="network") from exc


def _parse_pingcode(payload: Any) -> str:
    if isinstance(payload, dict):
        title = payload.get("title") or payload.get("name") or ""
        desc = payload.get("description") or payload.get("content") or payload.get("acceptance_criteria") or ""
        body = str(desc or "")
        # PingCode 部分接口返回 HTML 描述
        if body.strip().startswith("<"):
            body = _html_to_text(body)
        lines = [f"标题: {title}" if title else "", body]
        return "\n\n".join(x for x in lines if x)
    if isinstance(payload, list):
        return "\n\n".join(_parse_pingcode(item) for item in payload)
    return str(payload)


def fetch_url_content(url: str, *, kind: str | None = None) -> dict[str, str]:
    """抓取需求 URL，返回 {content, kind, title}。

    lanhu 在此只做识别引导（需证据包质量门禁）；pingcode/confluence 缺凭据 fail closed。
    """
    kind = kind or classify_url(url)
    if kind == "lanhu":
        raise RequirementSourceError(
            "蓝湖链接必须先通过「蓝湖证据包」质量门禁，再导入需求。请使用蓝湖入口提交。",
            kind="lanhu_gate",
        )

    if kind == "pingcode":
        token = settings.pingcode_api_token.strip()
        if not token:
            raise RequirementSourceError("未配置 PINGCODE_API_TOKEN，无法抓取 PingCode 需求", kind="auth")
        resp = _request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        if resp.status_code in (401, 403):
            raise RequirementSourceError("PingCode 凭据无效或无权访问该需求", kind="auth")
        if resp.status_code >= 400:
            raise RequirementSourceError(f"PingCode 返回 {resp.status_code}", kind="http")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise RequirementSourceError("PingCode 返回内容不是 JSON", kind="parse") from exc
        content = _parse_pingcode(payload)
        title = (payload.get("title") or payload.get("name") or "PingCode 需求") if isinstance(payload, dict) else "PingCode 需求"
        return {"content": content.strip(), "kind": kind, "title": str(title)}

    if kind == "confluence":
        token = settings.confluence_api_token.strip()
        if not token:
            raise RequirementSourceError("未配置 CONFLUENCE_API_TOKEN，无法抓取 Confluence 需求", kind="auth")
        resp = _request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        if resp.status_code in (401, 403):
            raise RequirementSourceError("Confluence 凭据无效或无权访问该页面", kind="auth")
        if resp.status_code >= 400:
            raise RequirementSourceError(f"Confluence 返回 {resp.status_code}", kind="http")
        try:
            payload = resp.json()
        except ValueError:
            payload = {}
        body = ""
        title = "Confluence 需求"
        if isinstance(payload, dict):
            title = payload.get("title") or title
            body = payload.get("body") or payload.get("value") or ""
            if isinstance(body, dict):
                body = body.get("value") or body.get("storage") or body.get("view") or ""
        content = _html_to_text(str(body)) if str(body).strip().startswith("<") else str(body)
        return {"content": content.strip(), "kind": kind, "title": str(title)}

    # generic HTML
    resp = _request(url, headers={"Accept": "text/html,application/xhtml+xml"})
    if resp.status_code >= 400:
        raise RequirementSourceError(f"需求地址返回 {resp.status_code}", kind="http")
    ctype = resp.headers.get("content-type", "")
    if "json" in ctype:
        try:
            payload = resp.json()
        except ValueError as exc:
            raise RequirementSourceError("需求地址返回的 JSON 无法解析", kind="parse") from exc
        content = _parse_pingcode(payload)
        title = (payload.get("title") or payload.get("name") or "在线需求") if isinstance(payload, dict) else "在线需求"
    else:
        content = _html_to_text(resp.text)
        title = _extract_title(resp.text) or "在线需求"
    return {"content": content.strip(), "kind": kind, "title": str(title)}


def _html_to_text(html: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(html or "")
    return parser.text()


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


# 供 PingCode 描述 HTML 复用（避免类型检查器对 feed 链式返回的告警）
def _parse_html_text(raw: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(raw or "")
    return parser.text()

