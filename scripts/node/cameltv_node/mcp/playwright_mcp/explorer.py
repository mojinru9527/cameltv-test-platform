"""M3 / TA-016：Playwright MCP Explorer PoC（13 号 §19 TA-016）。

- 输入：URL + 动作序列（click/fill/wait_for/text）；
- 输出：DOM、A11y、动作日志、证据（复用 batch-288 PlaywrightDriver）；
- 安全：域名 allowlist（精确/`*.example.com`），非 http(s)、IP 元数据一律拒绝；
- 不依赖 MCP SDK：暴露纯函数 `handle_tool()`，后续可薄封装为 MCP server。
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class DomainNotAllowed(ValueError):
    """URL 不在 allowlist 内。"""


class ExplorerError(RuntimeError):
    """动作/参数错误。"""


def assert_url_allowed(url: str, allowed_domains: list[str]) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise DomainNotAllowed(f"仅允许 http(s): {url}")
    host = (parts.hostname or "").lower().strip(".")
    if not host:
        raise DomainNotAllowed(f"缺少 host: {url}")
    for pattern in allowed_domains:
        candidate = pattern.lower().strip(".")
        if candidate.startswith("*."):
            suffix = candidate[2:]
            if host == suffix or host.endswith("." + suffix):
                return url
        elif host == candidate:
            return url
    raise DomainNotAllowed(f"域名不在 allowlist: {host}")


@dataclass
class ActionRecord:
    index: int
    action: str
    target: str
    ok: bool
    error: str | None = None
    duration_ms: int = 0


class PlaywrightExplorer:
    def __init__(self, *, allowed_domains: list[str], driver: Any) -> None:
        self.allowed_domains = list(allowed_domains)
        self.driver = driver

    def _perform(self, action: dict[str, Any]) -> None:
        kind = str(action.get("action") or "")
        selector = str(action.get("selector") or "")
        if kind == "click":
            self.driver.click(selector)
        elif kind == "fill":
            self.driver.fill(selector, str(action.get("value") or ""))
        elif kind == "wait_for":
            self.driver.wait_for(selector)
        elif kind == "text":
            self.driver.text(selector)
        else:
            raise ExplorerError(f"未知动作: {kind}")

    def explore(self, url: str, actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        assert_url_allowed(url, self.allowed_domains)
        started = time.monotonic()
        self.driver.goto(url)
        records = [
            ActionRecord(
                index=0,
                action="goto",
                target=url,
                ok=True,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        ]
        error: str | None = None
        for index, action in enumerate(actions or [], start=1):
            step_started = time.monotonic()
            try:
                self._perform(action)
                records.append(
                    ActionRecord(
                        index=index,
                        action=str(action.get("action")),
                        target=str(action.get("selector") or action.get("value") or ""),
                        ok=True,
                        duration_ms=int((time.monotonic() - step_started) * 1000),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - 记录首个失败并停止
                error = f"{type(exc).__name__}: {exc}"
                records.append(
                    ActionRecord(
                        index=index,
                        action=str(action.get("action")),
                        target=str(action.get("selector") or action.get("value") or ""),
                        ok=False,
                        error=error,
                        duration_ms=int((time.monotonic() - step_started) * 1000),
                    )
                )
                break

        artifacts = list(self.driver.capture_evidence())
        dom = _read_artifact(artifacts, "dom.html")
        a11y = _read_artifact(artifacts, "a11y.json")
        return {
            "url": url,
            "ok": error is None,
            "error": error,
            "dom": dom,
            "a11y": a11y,
            "actions": [asdict(record) for record in records],
            "artifacts": artifacts,
        }


def _read_artifact(artifacts: list[dict[str, Any]], name: str) -> str:
    for artifact in artifacts:
        if artifact.get("name") == name and artifact.get("path"):
            try:
                return Path(str(artifact["path"])).read_text(encoding="utf-8")
            except OSError:
                return ""
    return ""


TOOLS: dict[str, dict[str, Any]] = {
    "explore_page": {
        "description": "打开 allowlist 内页面，执行动作并返回 DOM/A11y/动作日志/证据",
        "input": {
            "url": "http(s) URL",
            "actions": "[{action: click|fill|wait_for|text, selector, value?}]",
        },
    }
}


def handle_tool(
    name: str, arguments: dict[str, Any], *, explorer: PlaywrightExplorer
) -> dict[str, Any]:
    if name != "explore_page":
        raise ExplorerError(f"未知工具: {name}")
    url = arguments.get("url")
    if not isinstance(url, str) or not url:
        raise ExplorerError("url 必填")
    actions = arguments.get("actions") or []
    if not isinstance(actions, list):
        raise ExplorerError("actions 必须是数组")
    return explorer.explore(url, actions)
