"""蓝湖(Lanhu) MCP Provider —— 统一的原型/需求提取来源。

从 ai_service.py 抽离（保持提取行为完全一致），供需求生成、知识中心 Raw Source、
Wiki 编译流水线统一复用。ai_service 通过 `from ... import _extract_lanhu_content` 委托调用。

- `_extract_lanhu_content(url, auto_login)`：原始提取，返回
  {content, page_filtered, folder_name, changelog, client_scope}，异常语义与原实现一致。
- `extract(url, auto_login)`：标准化入口，返回 LanhuExtractResult（永不抛异常，以状态表达失败）。
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


from app.core.config import settings


def _resolve_workspace_root() -> Path:
    """Resolve workspace root from config or auto-detect from this file's location.

    external/lanhu_provider.py 比原 services/ai_service.py 深一层，故多回退一级。
    """
    if settings.workspace_root:
        return Path(settings.workspace_root)
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent

def _lanhu_mcp_dir() -> Path:
    """Return the lanhu-mcp module directory."""
    if settings.lanhu_mcp_dir:
        return Path(settings.lanhu_mcp_dir)
    return _resolve_workspace_root() / "lanhu-mcp"


def _data_dir() -> Path:
    """Return the extracted data cache directory."""
    if settings.data_dir:
        return Path(settings.data_dir)
    return _resolve_workspace_root() / "test-platform-v2" / "backend" / "data"


# ── Changelog & Client Detection ──────────────────────────────

# Page name patterns that identify changelog / version history pages.
# These are now PRIORITIZED for extraction (not skipped).
_CHANGELOG_PAGE_PATTERNS = [
    "更新日志", "版本记录", "版本历史", "更新记录", "修订记录",
    "changelog", "version history", "revision history", "change log",
    "修订历史", "修改记录", "历史版本",
]

# Client platform detection patterns for folder/page names
_CLIENT_PATTERNS: dict[str, list[str]] = {
    "app": ["app端", "app", "移动端", "手机端", "android", "ios", "安卓", "苹果"],
    "pc": ["pc端", "pc", "桌面端", "电脑端", "windows", "mac", "客户端"],
    "web": ["web端", "web", "h5", "网页端", "浏览器", "h5端"],
}

# Cross-platform keywords
_CROSS_PLATFORM_KEYWORDS = ["三端", "全端", "通用", "多端", "所有端", "全平台"]


def _is_changelog_page(page_name: str) -> bool:
    """Return True if this page is a changelog / version history page.

    These pages are PRIORITIZED for extraction to identify versions.
    """
    name_lower = page_name.strip().lower()
    for pat in _CHANGELOG_PAGE_PATTERNS:
        if pat in name_lower:
            return True
    return False


def _detect_client_scope(name: str) -> list[str]:
    """Detect which client platforms a folder/page name suggests.

    Returns a list of client identifiers: ["app"], ["pc"], ["web"],
    or ["app", "pc", "web"] for cross-platform content.
    """
    name_lower = name.strip().lower()

    # Check cross-platform first
    for kw in _CROSS_PLATFORM_KEYWORDS:
        if kw in name_lower:
            return ["app", "pc", "web"]

    clients: list[str] = []
    for client_id, patterns in _CLIENT_PATTERNS.items():
        for pat in patterns:
            if pat in name_lower:
                if client_id not in clients:
                    clients.append(client_id)
                break

    return clients if clients else []


def _extract_changelog_text(changelog_pages: list[dict], resource_dir: str) -> str:
    """Extract text content from changelog pages.

    These pages are prioritized — they contain version information
    needed to guide the requirement extraction process.
    """
    parts: list[str] = []
    for p in changelog_pages:
        page_name = p.get("name", "")
        filename = p.get("filename", f'{page_name}.html')
        html_path = Path(resource_dir) / filename
        if html_path.exists():
            text = _extract_page_text(html_path)
            if text:
                parts.append(f"## {page_name}\n\n{text}")
    return "\n\n".join(parts)


def _analyze_version_structure_v2(all_pages: list[dict]) -> dict:
    """Analyze sitemap pages to identify version-folder structure with client detection.

    Enhanced version of _analyze_version_structure that additionally:
    - Detects client scope for each version group
    - Identifies changelog pages for prioritized extraction
    - Groups cross-platform pages separately

    Returns:
        {
            "has_version_structure": bool,
            "changelog_pages": [...],
            "version_groups": [{"name": str, "pages": [...], "client_scope": [...]}],
            "ungrouped_pages": [...],
            "cross_platform_pages": [...],
        }
    """
    changelog_pages: list[dict] = []
    version_groups_map: dict[str, list[dict]] = {}
    ungrouped_pages: list[dict] = []
    cross_platform_pages: list[dict] = []

    for p in all_pages:
        page_name = p.get("name", "")
        path: str = p.get("path", page_name)
        path_parts = [seg for seg in path.split("/") if seg]

        if len(path_parts) <= 1:
            if _is_changelog_page(page_name):
                changelog_pages.append(p)
            else:
                ungrouped_pages.append(p)
        else:
            top_folder = path_parts[0]
            # Check if this top folder is cross-platform
            folder_clients = _detect_client_scope(top_folder)
            if len(folder_clients) >= 3:
                cross_platform_pages.append(p)
            version_groups_map.setdefault(top_folder, []).append(p)

    version_groups = []
    for name, pages in version_groups_map.items():
        clients = _detect_client_scope(name)
        version_groups.append({
            "name": name,
            "pages": pages,
            "client_scope": clients,
        })

    has_version_structure = len(version_groups) >= 1

    return {
        "has_version_structure": has_version_structure,
        "changelog_pages": changelog_pages,
        "version_groups": version_groups,
        "ungrouped_pages": ungrouped_pages,
        "cross_platform_pages": cross_platform_pages,
    }


# ── Page Text Extraction ─────────────────────────────────────

# Max total chars for extracted page content (avoid overwhelming the AI).
_MAX_EXTRACTED_CHARS = 22000


def _extract_page_text(html_path: Path) -> str:
    """Extract clean visible text from a single Axure HTML page.

    Strips <script>, <style>, <noscript> and collapses whitespace.
    Returns the stripped text (may be empty for image-only pages).
    """
    from bs4 import BeautifulSoup as _BS

    html_content = html_path.read_text(encoding="utf-8", errors="replace")
    soup = _BS(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{3,}", "  ", text)
    return text.strip()


# ── Lanhu Content Extraction ─────────────────────────────────

async def _extract_lanhu_content(url: str, auto_login: bool = True) -> dict:
    """Extract text content from a Lanhu Axure document URL.

    CHANGELOG-FIRST PIPELINE:
    1. Download Axure resources (cached by version)
    2. Get sitemap → identify changelog pages + version structure + client scope
    3. Extract changelog text FIRST to understand versions
    4. Extract requirement content from version-grouped folders
    5. Tag content with detected client_scope

    Returns a dict with:
      - content: structured text for AI consumption
      - page_filtered: bool
      - folder_name: str
      - changelog: dict | None (parsed version info)
      - client_scope: list[str] (detected platforms)
    """
    sys.path.insert(0, str(_lanhu_mcp_dir()))
    try:
        from lanhu_mcp_server import (
            LanhuExtractor, LanhuAuthError, fix_html_files, lanhu_login,
            _save_cached_cookie,
        )

        _page_id = ''
        if 'pageId=' in url:
            m = re.search(r'pageId=([^&]+)', url)
            if m:
                _page_id = m.group(1)

        async def _do_extract(cookie_override: str = "", page_id: str = "") -> dict:
            extractor = LanhuExtractor(cookie=cookie_override)

            params = extractor.parse_url(url)
            doc_id = params["doc_id"]
            url_version_id = params.get("version_id", "")
            effective_url = url

            # ── Handle project-level URLs (no docId) ──
            if not doc_id:
                team_id = params.get("team_id", "")
                project_id = params.get("project_id", "")
                print(f"[ai_service] No docId in URL "
                      f"(tid={team_id[:8]}..., pid={project_id[:8]}...)")
                # Try to auto-discover the first document in the project
                try:
                    resp = await extractor.client.get(
                        f"https://lanhuapp.com/api/project/images"
                        f"?project_id={project_id}&team_id={team_id}"
                        f"&dds_status=1&position=1&show_cb_src=1&comment=1"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("code") == "00000":
                            images = data.get("data", {}).get("images", [])
                            if images:
                                doc_id = images[0].get("id")
                                doc_name_hint = images[0].get("name", "")
                                print(f"[ai_service] Auto-selected document: "
                                      f"'{doc_name_hint}' (id={doc_id[:16]}...) "
                                      f"from {len(images)} available")
                                sep = "&" if "?" in url.split("#")[-1] else "?"
                                effective_url = f"{url}{sep}docId={doc_id}"
                                params = extractor.parse_url(effective_url)
                                doc_id = params["doc_id"]
                except Exception:
                    pass  # Fall through to error message below

                if not doc_id:
                    raise ValueError(
                        "蓝湖链接缺少文档 ID（docId 参数）。\n\n"
                        "您当前提交的是蓝湖「项目」链接，需要改为具体的「设计文档」链接。\n\n"
                        "获取正确链接的方法：\n"
                        "1. 在浏览器中打开蓝湖项目\n"
                        "2. 点击左侧菜单中的具体设计稿名称\n"
                        "3. 复制浏览器地址栏中的完整 URL\n"
                        "4. 该 URL 应包含 docId= 参数\n\n"
                        f"当前链接: {url[:120]}..."
                    )

            resource_dir = str(_data_dir() / f"axure_extract_{doc_id[:8]}")
            download_result = await extractor.download_resources(
                effective_url, resource_dir, target_version_id=url_version_id,
            )

            if download_result["status"] in ["downloaded", "updated"]:
                fix_html_files(resource_dir)

            pages_info = await extractor.get_pages_list(effective_url)
            all_pages = pages_info["pages"]
            doc_name = pages_info.get("document_name", "设计稿")

            page_filtered = False
            folder_name = ""
            full_page_count = len(all_pages)
            detected_clients: list[str] = []
            changelog_content = ""

            # ── Page-level filtering (when pageId is in URL) ──
            if page_id:
                target_page = None
                for p in all_pages:
                    if p.get('id') == page_id:
                        target_page = p
                        break

                if target_page is None:
                    print(f"[ai_service] WARNING: page_id='{page_id}' not found in "
                          f"sitemap ({full_page_count} pages), falling back to full extraction")
                else:
                    target_parent_id = target_page.get('parent_id', '')
                    target_own_id = target_page.get('id', '')
                    folder_name = target_page.get('folder', '')
                    detected_clients = _detect_client_scope(folder_name)

                    filtered_pages = []
                    for p in all_pages:
                        pid = p.get('parent_id', '')
                        if p.get('id') == page_id:
                            filtered_pages.append(p)
                        elif pid and pid == target_parent_id:
                            filtered_pages.append(p)
                        elif pid and pid == target_own_id:
                            filtered_pages.append(p)

                    if filtered_pages:
                        page_filtered = True
                        all_pages = filtered_pages
                        print(f"[ai_service] Page-filtered extraction: {len(all_pages)}/"
                              f"{full_page_count} pages in folder '{folder_name}'")
                    else:
                        print(f"[ai_service] WARNING: page_id='{page_id}' matched but no "
                              f"pages passed filter, falling back to full extraction")
            else:
                # ── Version-aware changelog-first extraction ──
                structure = _analyze_version_structure_v2(all_pages)

                # Step 1: Extract changelog FIRST
                changelog_text = _extract_changelog_text(
                    structure["changelog_pages"], resource_dir
                )
                if changelog_text:
                    changelog_content = changelog_text
                    print(f"[ai_service] Changelog extracted: {len(structure['changelog_pages'])} "
                          f"pages, {len(changelog_text)} chars")

                # Step 2: Collect all detected client scopes
                for vg in structure["version_groups"]:
                    for c in vg.get("client_scope", []):
                        if c not in detected_clients:
                            detected_clients.append(c)
                # Also check ungrouped pages
                for p in structure["ungrouped_pages"]:
                    for c in _detect_client_scope(p.get("name", "")):
                        if c not in detected_clients:
                            detected_clients.append(c)
                # And cross-platform pages
                for p in structure["cross_platform_pages"]:
                    for c in _detect_client_scope(p.get("name", "")):
                        if c not in detected_clients:
                            detected_clients.append(c)

                if structure["has_version_structure"]:
                    print(f"[ai_service] Version-aware v2: {len(structure['version_groups'])} "
                          f"version groups, changelog={len(structure['changelog_pages'])} pages, "
                          f"clients={detected_clients} in '{doc_name}' ({full_page_count} pages)")

                    overall_max = _MAX_EXTRACTED_CHARS * 3
                    per_version_budget = max(
                        _MAX_EXTRACTED_CHARS,
                        overall_max // max(len(structure["version_groups"]), 1),
                    )

                    version_sections: list[str] = []
                    total_extracted = 0
                    total_empty = 0
                    total_truncated = False
                    extracted_version_count = 0

                    for vg in structure["version_groups"]:
                        vg_name = vg["name"]
                        vg_pages = vg["pages"]
                        vg_clients = vg.get("client_scope", [])
                        vg_texts: list[str] = []
                        vg_chars = 0
                        vg_truncated = False

                        # Add client scope hint in version header
                        client_hint = f" [{'/'.join(vg_clients)}]" if vg_clients else ""

                        for p in vg_pages:
                            page_name = p.get("name", "")
                            # We no longer skip changelog pages here — they're
                            # extracted separately above. But if a changelog page
                            # ended up inside a version group, still skip it
                            # (it's not requirement content).
                            if _is_changelog_page(page_name):
                                continue

                            filename = p.get("filename", f'{page_name}.html')
                            html_path = Path(resource_dir) / filename
                            if html_path.exists():
                                text = _extract_page_text(html_path)
                                if text:
                                    # Add per-page client scope hint
                                    page_clients = _detect_client_scope(page_name)
                                    page_client_tag = ""
                                    if page_clients and page_clients != vg_clients:
                                        page_client_tag = f" [{'/'.join(page_clients)}端]"

                                    entry = f"### {page_name}{page_client_tag}\n\n{text}"
                                    entry_chars = len(entry)
                                    if vg_chars + entry_chars > per_version_budget:
                                        vg_truncated = True
                                        remaining = per_version_budget - vg_chars
                                        if remaining > 200:
                                            vg_texts.append(
                                                f"### {page_name}\n\n{text[:remaining]}..."
                                                f"(内容已截断)"
                                            )
                                        break
                                    vg_texts.append(entry)
                                    vg_chars += entry_chars
                                else:
                                    total_empty += 1
                            else:
                                total_empty += 1

                        if vg_texts:
                            section = (
                                f"## 版本: {vg_name}{client_hint}\n\n"
                                + "\n\n".join(vg_texts)
                            )
                            version_sections.append(section)
                            total_extracted += len(vg_texts)
                            extracted_version_count += 1
                            if vg_truncated:
                                total_truncated = True

                    # Build version-aware summary with changelog info
                    vg_names = [vg["name"] for vg in structure["version_groups"]]
                    summary_parts = [
                        f"# 蓝湖设计稿「{doc_name}」版本化提取：\n"
                        f"共识别 {len(structure['version_groups'])} 个版本分组"
                        f"（{' / '.join(vg_names)}），",
                        f"已提取 {extracted_version_count} 个版本共 {total_extracted} 页"
                        f"（全文档共 {full_page_count} 页）",
                    ]
                    if detected_clients:
                        summary_parts.append(f"，涉及端: {'/'.join(detected_clients)}")
                    summary_parts.append(
                        (f"，更新日志 {len(structure['changelog_pages'])} 页" if structure["changelog_pages"] else "")
                        + (f"，{total_empty} 页无文本内容" if total_empty else "")
                        + ("，内容已截断" if total_truncated else "")
                        + "。\n"
                    )
                    summary = "".join(summary_parts)

                    if version_sections:
                        # Prepend changelog content if available
                        content_parts = [summary]
                        if changelog_content:
                            content_parts.append(
                                "\n\n# 版本更新日志（用于版本识别和需求溯源）\n\n"
                                + changelog_content
                                + "\n\n---\n\n# 各版本需求内容\n"
                            )
                        content_parts.append("\n\n".join(version_sections))
                        content_parts.append(f"\n\n---\n蓝湖链接: {effective_url}")

                        content = "\n".join(content_parts)
                        return {
                            "content": content,
                            "page_filtered": False,
                            "folder_name": "",
                            "changelog": {"raw": changelog_content} if changelog_content else None,
                            "client_scope": detected_clients,
                        }
                    else:
                        raise ValueError(
                            f"蓝湖设计稿「{doc_name}」共 {full_page_count} 页，"
                            f"识别到 {len(structure['version_groups'])} 个版本分组，"
                            f"但未能提取到有效的页面文本内容"
                            + (f"（{total_empty} 个页面无文本或HTML文件缺失）" if total_empty else "")
                            + "。请检查蓝湖链接是否正确，或原型页面是否包含可提取的文本内容。"
                        )

            # ── Flat extraction (no version structure or page-filtered) ──
            effective_max_chars = _MAX_EXTRACTED_CHARS
            if page_filtered:
                effective_max_chars = _MAX_EXTRACTED_CHARS * 4
            else:
                page_based = min(len(all_pages) * 2000, _MAX_EXTRACTED_CHARS * 3)
                effective_max_chars = max(_MAX_EXTRACTED_CHARS, page_based)

            page_texts: list[str] = []
            skipped_changelog: list[str] = []
            empty_pages: list[str] = []
            total_chars = 0
            truncated = False

            # If we have changelog content from version-aware analysis but
            # fell through to flat extraction, prepend it
            if changelog_content and not page_filtered:
                page_texts.append(
                    "# 版本更新日志（用于版本识别和需求溯源）\n\n"
                    + changelog_content
                    + "\n\n---\n\n# 需求内容\n"
                )
                total_chars = len(page_texts[0])

            for p in all_pages:
                page_name = p.get("name", "")
                # In flat extraction, skip changelog pages (already extracted above)
                if _is_changelog_page(page_name):
                    skipped_changelog.append(page_name)
                    continue

                filename = p.get("filename", f'{page_name}.html')
                html_path = Path(resource_dir) / filename
                if html_path.exists():
                    text = _extract_page_text(html_path)
                    if text:
                        entry = f"## {page_name}\n\n{text}"
                        entry_chars = len(entry)
                        if total_chars + entry_chars > effective_max_chars:
                            truncated = True
                            remaining = effective_max_chars - total_chars
                            if remaining > 200:
                                page_texts.append(f"## {page_name}\n\n{text[:remaining]}...(内容已截断)")
                            break
                        page_texts.append(entry)
                        total_chars += entry_chars
                    else:
                        empty_pages.append(page_name)
                else:
                    empty_pages.append(page_name)

            # Build summary
            if page_filtered:
                summary_parts = [
                    f"蓝湖设计稿「{doc_name}」-> 「{folder_name}」模块提取："
                ]
                summary_parts.append(
                    f"模块共 {len(all_pages)} 页（全文档共 {full_page_count} 页），"
                    f"已提取 {len(page_texts)} 页"
                )
            else:
                summary_parts = [f"蓝湖设计稿「{doc_name}」内容提取："]
                summary_parts.append(
                    f"共 {len(all_pages)} 页，已提取 {len(page_texts)} 页"
                )
            if detected_clients:
                summary_parts.append(f"，涉及端: {'/'.join(detected_clients)}")
            summary_parts.append(
                (f"，更新日志 {len(skipped_changelog)} 页（已优先提取）" if skipped_changelog else "")
                + (f"，{len(empty_pages)} 页无文本内容" if empty_pages else "")
                + ("，内容已截断" if truncated else "")
                + "。\n"
            )
            summary = "".join(summary_parts)

            if page_texts:
                return {
                    "content": summary + "\n\n---\n\n".join(page_texts) + f"\n\n---\n蓝湖链接: {effective_url}",
                    "page_filtered": page_filtered,
                    "folder_name": folder_name,
                    "changelog": {"raw": changelog_content} if changelog_content else None,
                    "client_scope": detected_clients,
                }
            else:
                raise ValueError(
                    f"蓝湖设计稿「{doc_name}」共 {full_page_count} 页，"
                    f"但未能提取到有效的页面文本内容"
                    + (f"（{len(empty_pages)} 个页面无文本或HTML文件缺失）" if empty_pages else "")
                    + "。请检查蓝湖链接是否正确，或原型页面是否包含可提取的文本内容。"
                )

        # Try extraction with current cookie
        try:
            return await _do_extract(page_id=_page_id)
        except LanhuAuthError as e:
            if not auto_login:
                raise ValueError(
                    f"蓝湖认证失败，Cookie 已过期。"
                    f"请在 .env 中设置 LANHU_USERNAME 和 LANHU_PASSWORD 以启用自动登录，"
                    f"或手动获取 Cookie 填入 LANHU_COOKIE。\n"
                    f"错误详情: {str(e)[:200]}"
                )
            print(f"[ai_service] Lanhu auth failed: {e}. Attempting auto-login...")
            try:
                new_cookie = await lanhu_login()
                if new_cookie:
                    _save_cached_cookie(new_cookie)
                    print("[ai_service] Auto-login succeeded, retrying extraction with new cookie...")
                    return await _do_extract(cookie_override=new_cookie, page_id=_page_id)
                else:
                    raise ValueError(
                        "蓝湖自动登录失败：未获取到有效的 Cookie。"
                        "请检查 .env 中的 LANHU_USERNAME 和 LANHU_PASSWORD 是否正确。"
                    )
            except LanhuAuthError as login_err:
                raise ValueError(
                    f"蓝湖自动登录失败: {str(login_err)[:200]}。"
                    f"请检查 .env 中的 LANHU_USERNAME 和 LANHU_PASSWORD 是否正确，"
                    f"或手动获取 Cookie 填入 LANHU_COOKIE。"
                )
            except Exception as login_err:
                raise ValueError(
                    f"蓝湖自动登录时发生未知错误: {str(login_err)[:200]}。"
                    f"请手动获取 Cookie 填入 LANHU_COOKIE。"
                )

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(
            f"蓝湖设计稿内容提取失败: {str(e)[:300]}。"
            f"请检查蓝湖链接是否有效，或稍后重试。"
        )
    finally:
        if str(_lanhu_mcp_dir()) in sys.path:
            sys.path.remove(str(_lanhu_mcp_dir()))


# ── 标准化 Provider 接口（供需求 / 知识中心 Raw Source / Wiki 编译复用）──

_AUTH_HINTS = ("登录", "LANHU_USERNAME", "LANHU_PASSWORD", "LANHU_COOKIE", "cookie", "认证", "登录态")
_PERM_HINTS = ("无权", "权限不足", "没有权限", "permission")
_IMAGE_HINTS = ("图片", "补充说明", "无法提取", "image", "无文本")
_PARTIAL_HINTS = ("部分", "partial")
_INVALID_URL_HINTS = ("docId", "pageId", "文档链接", "项目链接", "设计稿页面")


def _classify_error_status(msg: str) -> str:
    """把原始提取抛出的 ValueError 文案归类为标准 extraction_status。"""
    text = msg or ""
    if any(h in text for h in _AUTH_HINTS):
        return "auth_failed"
    if any(h in text for h in _PERM_HINTS):
        return "permission_denied"
    if any(h in text for h in _IMAGE_HINTS):
        return "image_only"
    if any(h in text for h in _INVALID_URL_HINTS):
        return "invalid_url"
    return "failed"


def parse_lanhu_ids(url: str) -> tuple[str, str, str]:
    """从蓝湖 URL 解析 docId / versionId / pageId（本地正则，不触网）。

    Returns (doc_id, version_id, page_id). page_id 为可选——当 URL 不含 pageId 时
    表示整文档导入。
    """
    def _grab(param: str) -> str:
        m = re.search(param + r"=([^&#]+)", url or "")
        return m.group(1) if m else ""
    return _grab("docId"), _grab("versionId"), _grab("pageId")


# 向后兼容别名：旧调用方仍可使用 _parse_url_ids
_parse_url_ids = parse_lanhu_ids


def build_immutable_version(doc_id: str, version_id: str, page_id: str | None) -> str:
    """构建标准化的蓝湖 immutable_version。

    格式: lanhu:{docId}:{versionId}:{pageId}
    page_id 为空时省略末尾段: lanhu:{docId}:{versionId}

    示例:
        build_immutable_version("doc-123", "ver-456", "page-789")
        -> "lanhu:doc-123:ver-456:page-789"

        build_immutable_version("doc-123", "ver-456", None)
        -> "lanhu:doc-123:ver-456"
    """
    parts = [p for p in (doc_id, version_id, page_id) if p]
    return "lanhu:" + ":".join(parts)


async def extract(url: str, auto_login: bool = True):
    """标准化蓝湖提取入口。

    永不抛异常：所有失败以 LanhuExtractResult.extraction_status 表达
    （success/partial/image_only/auth_failed/permission_denied/invalid_url/failed），
    便于需求模块、知识中心、Wiki 统一按状态提示与入库。
    """
    from app.schemas.lanhu import LanhuExtractResult

    doc_id, version_id, page_id = _parse_url_ids(url)
    if not doc_id and not page_id:
        return LanhuExtractResult(
            source_ref=url, doc_id=doc_id, version_id=version_id, page_id=page_id,
            extraction_status="invalid_url",
            extraction_summary="链接缺少 docId/pageId，请复制具体设计稿页面链接",
        )

    try:
        raw = await _extract_lanhu_content(url, auto_login=auto_login)
    except ValueError as e:
        return LanhuExtractResult(
            source_ref=url, doc_id=doc_id, version_id=version_id, page_id=page_id,
            extraction_status=_classify_error_status(str(e)),
            extraction_summary=str(e)[:500],
        )
    except Exception as e:  # noqa: BLE001 — 兜底，绝不影响调用方
        return LanhuExtractResult(
            source_ref=url, doc_id=doc_id, version_id=version_id, page_id=page_id,
            extraction_status="failed", extraction_summary=str(e)[:500],
        )

    content = (raw.get("content") or "").strip()
    folder_name = raw.get("folder_name") or ""
    client_scope = raw.get("client_scope") or []
    changelog = raw.get("changelog") or {}
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else ""
    if doc_id:
        immutable_version = build_immutable_version(doc_id, version_id, page_id or None)
    else:
        immutable_version = content_hash  # 非蓝湖来源退化为 content_hash

    if not content:
        status, summary = "image_only", "原型无可提取文本（可能为图片），请填写补充说明"
    else:
        scope_txt = "/".join(client_scope) if client_scope else "未标注端"
        # partial: 提取成功但部分页面无文本（content 中包含「无文本内容」提示）
        if "无文本内容" in content or "页面无文本" in content:
            status = "partial"
        else:
            status = "success"
        summary = f"提取成功，约 {len(content)} 字，模块「{folder_name or '未分组'}」，端范围 {scope_txt}"

    return LanhuExtractResult(
        source_ref=url,
        doc_id=doc_id, version_id=version_id, page_id=page_id,
        module_name=folder_name,
        client_scope=client_scope,
        changelog=changelog,
        content_md=content,
        content_hash=content_hash,
        immutable_version=immutable_version,
        extraction_status=status,
        extraction_summary=summary,
    )


# ── 证据包专用：下载资源 + 返回全页面树（供滚动截图与 OCR）──

async def get_lanhu_pages_for_evidence(url: str) -> dict:
    """下载 Axure 资源并返回全页面列表，供证据包截图/OCR 使用。

    与 `_extract_lanhu_content` 共用下载与认证重试逻辑，但不做文本聚合：
    只返回 resource_dir、document_name 和规范化 pages（含 filename / folder /
    local_url），让 screenshot_service 逐页滚动截图、OCR。

    Return:
        {"status": "success", "resource_dir": str, "document_name": str,
         "pages": [{"id","name","path","folder","filename","local_url"}, ...]}
    异常统一以 status="failed" + error 表达，绝不裸抛。
    """
    sys.path.insert(0, str(_lanhu_mcp_dir()))
    try:
        from lanhu_mcp_server import (  # type: ignore
            LanhuAuthError,
            LanhuExtractor,
            fix_html_files,
            lanhu_login,
            _save_cached_cookie,
        )

        async def _do(cookie_override: str = "") -> dict:
            extractor = LanhuExtractor(cookie=cookie_override)
            params = extractor.parse_url(url)
            doc_id = params.get("doc_id", "")
            url_version_id = params.get("version_id", "")
            if not doc_id:
                raise ValueError("蓝湖链接缺少 docId，请复制具体设计稿页面链接")

            resource_dir = str(_data_dir() / f"axure_extract_{doc_id[:8]}")
            download_result = await extractor.download_resources(
                url, resource_dir, target_version_id=url_version_id,
            )
            if download_result.get("status") in ("downloaded", "updated"):
                fix_html_files(resource_dir)

            pages_info = await extractor.get_pages_list(url)
            document_name = pages_info.get("document_name", "设计稿")

            pages: list[dict] = []
            for p in pages_info.get("pages", []):
                name = p.get("name", "")
                folder = p.get("folder", "")
                filename = p.get("filename", f"{name}.html")
                path = f"{folder}/{name}" if folder else name
                html_path = Path(resource_dir) / filename
                local_url = html_path.as_uri() if html_path.exists() else ""
                pages.append({
                    "id": p.get("id", ""),
                    "name": name,
                    "path": path,
                    "folder": folder,
                    "filename": filename,
                    "local_url": local_url,
                })

            return {
                "status": "success",
                "resource_dir": resource_dir,
                "document_name": document_name,
                "pages": pages,
            }

        try:
            return await _do()
        except LanhuAuthError:
            new_cookie = await lanhu_login()
            if new_cookie:
                _save_cached_cookie(new_cookie)
                return await _do(cookie_override=new_cookie)
            return {"status": "failed", "error": "蓝湖认证失败且自动登录未获取到 Cookie", "pages": []}
    except Exception as e:  # noqa: BLE001 — 统一以状态表达失败
        return {"status": "failed", "error": str(e)[:300], "pages": []}
    finally:
        if str(_lanhu_mcp_dir()) in sys.path:
            sys.path.remove(str(_lanhu_mcp_dir()))

