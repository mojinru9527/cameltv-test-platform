"""蓝湖页面树发现 —— 解析蓝湖 URL 与规范化全页面树。

不再只处理传入的 pageId：`discover_pages` 默认返回整份 sitemap（全页面树），
以便证据包对每个需求页面都留存截图 + OCR + DOM 文本。纯函数（parse_lanhu_url /
normalize_pages）可确定性单测；`discover_pages` 通过 lanhu_provider 下载资源并读取页面列表。
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass
class LanhuUrlParts:
    url: str
    doc_id: str = ""
    version_id: str = ""
    page_id: str = ""
    project_id: str = ""
    team_id: str = ""


def parse_lanhu_url(url: str) -> LanhuUrlParts:
    """解析蓝湖 URL 中的 docId/versionId/pageId/pid/tid。

    支持 hash 型 query（`#/...?docId=...`）：优先取 fragment 中 `?` 之后的部分。
    """
    parsed = urlparse(url)
    raw = parsed.query
    if parsed.fragment and "?" in parsed.fragment:
        raw = parsed.fragment.split("?", 1)[1]
    qs = parse_qs(raw)

    def one(key: str) -> str:
        return (qs.get(key) or [""])[0]

    return LanhuUrlParts(
        url=url,
        doc_id=one("docId"),
        version_id=one("versionId"),
        page_id=one("pageId"),
        project_id=one("pid"),
        team_id=one("tid"),
    )


@dataclass
class DiscoveredLanhuPage:
    page_id: str
    page_name: str
    page_path: str
    folder: str
    order_index: int
    page_url: str = ""
    local_url: str = ""


def _folder_from_path(page_path: str) -> str:
    """路径去掉末段（页面名）即为所属文件夹。'App/赛事/比赛推送' -> 'App/赛事'。"""
    if not page_path or "/" not in page_path:
        return ""
    return page_path.rsplit("/", 1)[0]


def normalize_pages(raw_pages: list[dict]) -> list[DiscoveredLanhuPage]:
    """把原始页面 dict 列表规范化为有序的 DiscoveredLanhuPage 列表。

    保持传入顺序作为 order_index。folder 从 path 推导；page_url/local_url 透传（若已提供）。
    """
    pages: list[DiscoveredLanhuPage] = []
    for idx, raw in enumerate(raw_pages):
        page_id = str(raw.get("id") or raw.get("page_id") or "")
        page_name = str(raw.get("name") or raw.get("page_name") or "")
        page_path = str(raw.get("path") or raw.get("page_path") or page_name)
        folder = str(raw.get("folder") or _folder_from_path(page_path))
        pages.append(
            DiscoveredLanhuPage(
                page_id=page_id,
                page_name=page_name,
                page_path=page_path,
                folder=folder,
                order_index=idx,
                page_url=str(raw.get("page_url") or ""),
                local_url=str(raw.get("local_url") or ""),
            )
        )
    return pages


def _build_page_url(base: LanhuUrlParts, page_id: str) -> str:
    """用原始 docId/versionId + 目标 pageId 拼出稳定的蓝湖页面 URL（保留可追溯性）。"""
    if not base.doc_id:
        return base.url
    q = (
        f"tid={base.team_id}&pid={base.project_id}"
        f"&versionId={base.version_id}&docId={base.doc_id}"
        f"&docType=axure&pageId={page_id}"
    )
    return f"https://lanhuapp.com/web/#/item/project/product?{q}"


def discover_pages(url: str, capture_all_pages: bool = True) -> list[DiscoveredLanhuPage]:
    """发现蓝湖页面树。

    1. 解析 ids。
    2. 通过 lanhu_provider 下载资源并取全页面列表。
    3. capture_all_pages=True → 返回 sitemap 全序；False → 仅根页面及其同级文件夹。
    4. 用原始 docId/versionId/pageId 构造 page_url；若已下载 Axure html 则填 local_url。
    """
    import asyncio

    from app.services.external import lanhu_provider

    base = parse_lanhu_url(url)
    result = asyncio.run(lanhu_provider.get_lanhu_pages_for_evidence(url))
    if result.get("status") != "success":
        raise ValueError(result.get("error") or "蓝湖页面发现失败")

    raw_pages = list(result.get("pages") or [])
    if not capture_all_pages and base.page_id:
        target = next((p for p in raw_pages if str(p.get("id")) == base.page_id), None)
        if target is not None:
            folder = target.get("folder", "")
            raw_pages = [p for p in raw_pages if p.get("folder", "") == folder] or [target]

    pages = normalize_pages(raw_pages)
    for p in pages:
        p.page_url = _build_page_url(base, p.page_id)
    return pages
