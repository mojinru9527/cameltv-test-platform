"""滚动感知截图服务 —— full_page + 视口分段 + 内部滚动容器 + 去重。

解决「长页面/Axure 动态面板截不全」：
  - compute_scroll_positions：纯函数，规划分段滚动位置（可确定性单测）。
  - capture_page_segments：Playwright 逐段滚动截图；短页面单段，长页面多段。
  - 内部滚动容器检测：body 短但存在可滚动子容器时，滚动最大容器。
  - 去重保护：连续两段截图 SHA-256 相同则提前停止（滚动到底或无变化）。
  - 上限保护：max_segments 防止无限滚动。

浏览器截图为 IO/环境相关，靠手工 smoke 与可选集成测试覆盖；此处只保证规划纯函数确定性。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings


def compute_scroll_positions(
    scroll_height: int,
    viewport_height: int,
    step_ratio: float,
    max_segments: int,
) -> list[int]:
    """规划滚动位置：覆盖整页且不超过 max_segments。短页面返回 [0]。"""
    if scroll_height <= 0 or viewport_height <= 0:
        return [0]
    if scroll_height <= viewport_height:
        return [0]
    step = max(1, int(viewport_height * step_ratio))
    positions = [0]
    pos = 0
    while pos + viewport_height < scroll_height and len(positions) < max_segments:
        pos = min(pos + step, scroll_height - viewport_height)
        if pos != positions[-1]:
            positions.append(pos)
        else:
            break
    return positions


@dataclass
class CaptureSegment:
    path: Path
    scroll_top: int
    viewport_height: int
    sha256: str = ""


@dataclass
class CaptureResult:
    segments: list[CaptureSegment] = field(default_factory=list)
    scroll_height: int = 0
    viewport_height: int = 0
    duplicate_stop: bool = False
    inner_container: str = ""
    error: str = ""


_METRICS_JS = """() => ({
    scrollHeight: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
    clientHeight: window.innerHeight,
    scrollWidth: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),
    clientWidth: window.innerWidth
})"""

_INNER_SCROLL_JS = """() => Array.from(document.querySelectorAll('*'))
  .filter(el => el.scrollHeight > el.clientHeight + 20)
  .map((el, idx) => ({
    index: idx,
    id: el.id || "",
    className: (el.className && el.className.toString) ? el.className.toString() : "",
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight
  }))
  .sort((a, b) => b.scrollHeight - a.scrollHeight)
  .slice(0, 20)"""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


async def capture_page_segments(page_url: str, output_dir: Path, page_key: str) -> CaptureResult:
    """打开页面并逐段滚动截图；返回 CaptureResult（含 segments 与质量标记）。

    需要 Playwright（`playwright` + chromium）。失败以 CaptureResult.error 表达，绝不裸抛。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.async_api import async_playwright
    except Exception as e:  # noqa: BLE001
        return CaptureResult(error=f"playwright 不可用: {e}")

    vw = settings.lanhu_capture_viewport_width
    vh = settings.lanhu_capture_viewport_height
    wait_ms = settings.lanhu_capture_wait_ms
    step_ratio = settings.lanhu_capture_scroll_step_ratio
    max_segments = settings.lanhu_capture_max_segments_per_page

    result = CaptureResult()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": vw, "height": vh})
            await page.goto(page_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(wait_ms)

            metrics = await page.evaluate(_METRICS_JS)
            scroll_height = int(metrics["scrollHeight"])
            client_height = int(metrics["clientHeight"])
            result.scroll_height = scroll_height
            result.viewport_height = client_height

            # body 短但存在内部滚动容器 → 改滚动最大容器
            inner_selector = ""
            if scroll_height <= client_height + 20:
                containers = await page.evaluate(_INNER_SCROLL_JS)
                if containers:
                    top = containers[0]
                    if top.get("id"):
                        inner_selector = f"#{top['id']}"
                    else:
                        # 注入稳定选择器
                        await page.evaluate(
                            """(idx) => {
                              const els = Array.from(document.querySelectorAll('*'))
                                .filter(el => el.scrollHeight > el.clientHeight + 20)
                                .sort((a,b) => b.scrollHeight - a.scrollHeight);
                              if (els[0]) els[0].setAttribute('data-evidence-scroll-target','1');
                            }""",
                            0,
                        )
                        inner_selector = "[data-evidence-scroll-target='1']"
                    scroll_height = int(top["scrollHeight"])
                    client_height = int(top["clientHeight"])
                    result.inner_container = inner_selector
                    result.scroll_height = scroll_height
                    result.viewport_height = client_height

            positions = compute_scroll_positions(scroll_height, client_height, step_ratio, max_segments)

            prev_hash = ""
            for idx, top in enumerate(positions):
                if inner_selector:
                    await page.evaluate(
                        """({selector, y}) => { const el = document.querySelector(selector); if (el) el.scrollTop = y; }""",
                        {"selector": inner_selector, "y": top},
                    )
                else:
                    await page.evaluate("(y) => window.scrollTo(0, y)", top)
                await page.wait_for_timeout(wait_ms)

                path = output_dir / f"{page_key}-segment-{idx + 1:03d}.png"
                await page.screenshot(path=str(path), full_page=False)
                digest = _sha256_file(path)

                if digest == prev_hash:
                    # 连续两段视觉内容相同 → 去重并停止（滚动到底/无变化）
                    path.unlink(missing_ok=True)
                    result.duplicate_stop = True
                    break
                prev_hash = digest
                result.segments.append(
                    CaptureSegment(path=path, scroll_top=top, viewport_height=client_height, sha256=digest)
                )

            await browser.close()
    except Exception as e:  # noqa: BLE001
        result.error = str(e)[:300]
    return result
