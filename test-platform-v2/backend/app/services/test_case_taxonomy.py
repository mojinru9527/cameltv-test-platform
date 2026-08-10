"""Deterministic test-case taxonomy normalization.

Historical sports cases used domains, client channels, and page variants as
interchangeable hierarchy levels.  The product taxonomy is instead:

    surface -> functional domain -> functional module path

Client channels remain coverage metadata and must not split the functional
tree.  This module is intentionally pure so the API, import scripts, and data
quality audit share exactly one set of rules.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


LEGACY_USER_DOMAINS = frozenset({
    "个人中心", "赛事详情", "直播间", "app端数据与排行榜", "资讯", "首页",
    "pc端", "搜索", "登录注册", "启动引导", "支付与账户", "ugc内容",
    "web端", "骆驼币系统", "广告系统", "银钻系统", "ugc功能", "银钻预测",
    "付费活动", "faq帮助", "ugc", "商城", "回放", "球员", "球队", "直播",
    "聊天弹幕", "联赛", "装扮", "钱包财务", "银钻任务", "预测pick", "通用",
    "启动登录",
})
LEGACY_ADMIN_DOMAINS = frozenset({
    "财务管理", "ugc管理", "商城管理", "消息管理", "赛事预测", "广告管理",
    "活动管理", "银钻任务管理", "风控管理", "装扮管理", "系统管理",
    "球队及联赛管理", "ugc", "内容管理", "商城", "推流主播", "更新日志",
    "球队及联赛", "用户管理", "赛事视频流", "银钻任务",
})

_PATH_SEPARATOR_RE = re.compile(r"[/\\>＞]+")
_SURFACE_PREFIX_RE = re.compile(
    r"^(?:(?:体育平台|体育)\s*[-_/]?\s*)?"
    r"(?:用户端|运营后台|管理后台|接口测试|接口)"
    r"(?:\s*[-_/]?\s*功能)?"
    r"(?:\s*[-/\\>＞]\s*)?",
    re.IGNORECASE,
)
_TERMINAL_SUFFIX_RE = re.compile(
    r"(?:"
    r"[（(]\s*(?:pc(?:\s*[-_]?\s*web)?|web|mb|移动端?(?:\s*[-_]?\s*web)?|"
    r"安卓(?:\s*[/+]?\s*ios)?|android(?:\s*[/+]?\s*ios)?|ios)\s*[)）]"
    r"|[_\-\s]+(?:pc(?:[-_\s]?web|端)?|web端?|mb|移动端?(?:[-_\s]?web)?)"
    r"|(?:pc(?:[-_\s]?web|端)|web端|移动端?(?:[-_\s]?web))"
    r")[_\-\s]*$",
    re.IGNORECASE,
)

_TERMINAL_TOKENS = frozenset({
    "pc", "pcweb", "pc端", "web", "web端", "mb", "mobile", "mobileweb",
    "移动", "移动端", "移动web", "移动端web", "安卓", "安卓ios", "android",
    "androidios", "ios",
})
_GENERIC_TOKENS = frozenset({
    "体育", "体育平台", "体育平台模块", "功能", "用户端", "运营后台", "管理后台",
    "接口", "接口测试",
})
_SEGMENT_ALIASES = {
    "赛事详情页": "赛事详情",
    "赛事回放列表": "回放",
    "赛事回放入口": "回放",
    "赛事回放详情": "回放",
    "camel商城": "商城",
    "faq": "FAQ帮助",
}


@dataclass(frozen=True, slots=True)
class CaseTaxonomyLocation:
    surface: str
    domain: str
    module_path: str
    terminal_scopes: tuple[str, ...] = ()


def classify_case_surface(domain: str, case_type: str) -> str:
    """Classify the product surface without changing persisted values."""
    normalized = (domain or "").strip().lower()
    if case_type == "api" or "接口" in normalized:
        return "接口测试"
    if any(keyword in normalized for keyword in ("运营后台", "管理后台", "后台", "admin")):
        return "运营后台"
    if any(keyword in normalized for keyword in (
        "用户端", "客户端", "前台", "pc端", "移动端", "app端", "web端",
    )):
        return "用户端"
    if normalized in LEGACY_ADMIN_DOMAINS:
        return "运营后台"
    if normalized in LEGACY_USER_DOMAINS:
        return "用户端"
    return "其他"


def extract_terminal_scopes(*values: str) -> tuple[str, ...]:
    """Return canonical client-channel labels found in historical fields."""
    text = " ".join(value or "" for value in values)
    scopes: list[str] = []
    if re.search(r"安卓\s*[/+]?\s*i?os|android(?:\s*[/+]?\s*ios)?|\bios\b", text, re.I):
        scopes.append("安卓/iOS")
    if re.search(r"pc\s*[-_]?\s*web|pc端|_pc_|[（(]\s*pc\s*[)）]", text, re.I):
        scopes.append("PC Web")
    if re.search(r"移动端?(?:\s*[-_]?\s*web)?|mobile(?:\s*[-_]?\s*web)?|_mb_|_移动_", text, re.I):
        scopes.append("移动 Web")
    return tuple(scopes)


def _token_key(value: str) -> str:
    return re.sub(r"[\s_\-()/（）+]+", "", value).lower()


def _normalize_segment(value: str) -> str:
    segment = (value or "").strip().strip("_-")
    if not segment:
        return ""
    if _token_key(segment) in _TERMINAL_TOKENS | _GENERIC_TOKENS:
        return ""
    previous = None
    while previous != segment:
        previous = segment
        segment = _TERMINAL_SUFFIX_RE.sub("", segment).strip().strip("_-")
    if not segment or _token_key(segment) in _TERMINAL_TOKENS | _GENERIC_TOKENS:
        return ""
    alias = _SEGMENT_ALIASES.get(segment.lower())
    if alias:
        return alias
    if segment.lower().startswith("ugc"):
        return "UGC" + segment[3:]
    return segment


def _domain_segments(domain: str) -> list[str]:
    raw = (domain or "").strip()
    without_surface = _SURFACE_PREFIX_RE.sub("", raw, count=1).strip(" /\\>＞_-")
    if _token_key(without_surface) in _GENERIC_TOKENS:
        without_surface = ""
    return [
        normalized
        for part in _PATH_SEPARATOR_RE.split(without_surface)
        if (normalized := _normalize_segment(part))
    ]


def _module_segments(module: str) -> list[str]:
    return [
        normalized
        for part in _PATH_SEPARATOR_RE.split(module or "")
        if (normalized := _normalize_segment(part))
    ]


def _merge_paths(domain_parts: list[str], module_parts: list[str]) -> list[str]:
    if not domain_parts:
        combined = list(module_parts)
    elif not module_parts:
        combined = list(domain_parts)
    else:
        overlap = 0
        limit = min(len(domain_parts), len(module_parts))
        for size in range(1, limit + 1):
            if domain_parts[-size:] == module_parts[:size]:
                overlap = size
        combined = [*domain_parts, *module_parts[overlap:]]

    deduped: list[str] = []
    for part in combined:
        if not deduped or deduped[-1] != part:
            deduped.append(part)
    return deduped


def canonical_case_location(
    domain: str,
    module: str,
    case_type: str,
) -> CaseTaxonomyLocation:
    """Normalize a persisted case into the product-facing functional tree."""
    surface = classify_case_surface(domain, case_type)
    parts = _merge_paths(_domain_segments(domain), _module_segments(module))
    if not parts:
        parts = ["未分类"]
    return CaseTaxonomyLocation(
        surface=surface,
        domain=parts[0],
        module_path="/".join(parts[1:]),
        terminal_scopes=extract_terminal_scopes(domain, module),
    )


def taxonomy_location_matches(
    location: CaseTaxonomyLocation,
    *,
    surface: str = "",
    domain: str = "",
    module_path: str = "",
    direct_only: bool = False,
) -> bool:
    """Match a canonical node; module parents include every descendant.

    direct_only=True 时只匹配"精确归属该节点、无下一层子模块路径"的直属用例：
    模块级直属 = module_path 精确相等；域级直属 = module_path 为空。
    """
    if surface and location.surface != surface:
        return False
    if domain and location.domain != domain:
        return False
    if module_path:
        if direct_only:
            return location.module_path == module_path
        return (
            location.module_path == module_path
            or location.module_path.startswith(f"{module_path}/")
        )
    if direct_only:
        return location.module_path == ""
    return True
