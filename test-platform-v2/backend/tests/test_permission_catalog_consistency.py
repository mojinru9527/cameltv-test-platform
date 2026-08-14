"""Batch 179（FIX-173-P2-07）：权限码单点目录一致性校验。

路由层 `require_permission("...")` 与 seed.py 权限目录（_MENUS/_ACTIONS）当前为
双份字符串维护。本测试扫描全部路由文件，比对引用的权限码是否都能在 seed 目录
中找到——任何一端改名/新增而不同步都会在此变红，防止「权限静默失效」的定时炸弹。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROUTES_DIR = Path(__file__).resolve().parents[1] / "app" / "api" / "v1"
SEED_FILE = Path(__file__).resolve().parents[1] / "app" / "seed.py"

# 路由中引用权限码的两种模式：
# 1) require_permission("xxx")
# 2) 变量声明如 permission="xxx" / require_permission(f"xxx")（静态前缀场景少见，仅匹配字面量）
_PERM_REF = re.compile(r'require_permission\(\s*["\']([a-z0-9:_-]+)["\']')
_PERM_REF2 = re.compile(r'permission\s*=\s*["\']([a-z0-9:_-]+)["\']')
# 路由内直接检查权限的集合写法（如 "xxx" in current.permissions）
_INLINE_REF = re.compile(r'["\']([a-z0-9:_-]+)["\']\s+in\s+current\.permissions')


def _seed_permission_codes() -> set[str]:
    text = SEED_FILE.read_text(encoding="utf-8")
    codes = set()
    for m in re.finditer(r'^\s*\(\s*["\']([a-z0-9:_-]+)["\']', text, re.MULTILINE):
        codes.add(m.group(1))
    return codes


def _route_permission_refs() -> set[str]:
    refs: set[str] = set()
    for path in ROUTES_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        refs.update(_PERM_REF.findall(text))
        refs.update(_PERM_REF2.findall(text))
        refs.update(_INLINE_REF.findall(text))
    return refs


def test_all_route_permissions_exist_in_seed_catalog():
    """路由引用的每个权限码都必须在 seed 目录中存在（防静默失效）。"""
    seed_codes = _seed_permission_codes()
    route_refs = _route_permission_refs()
    missing = sorted(route_refs - seed_codes)
    assert not missing, (
        f"路由引用了 seed 目录不存在的权限码（权限将恒为 False，静默失效）: {missing}"
    )


def test_no_obvious_typo_duplicates_in_route_refs():
    """路由引用的权限码不应有仅大小写不同的孪生码（常见笔误源）。"""
    route_refs = _route_permission_refs()
    lowered: dict[str, set[str]] = {}
    for code in route_refs:
        lowered.setdefault(code.lower(), set()).add(code)
    twins = {v for v in lowered.values() if len(v) > 1}
    assert not twins, f"疑似大小写笔误的权限码: {twins}"
