"""C115 — 关联基座加载与模块关联上下文（用例生成提示注入，用户方向闭环）。

从 docs/体育平台-关联基座.json 读取「模块-接口-功能-后台-konfi」关联，
为用例生成提示注入指定模块的关联上下文，生成前先按关联定位（C112-1 落地的生成侧消费）。
"""
from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BASELINE = _REPO_ROOT / "docs" / "体育平台-关联基座.json"
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(_BASELINE.read_text(encoding="utf-8"))
    return _cache


def association_context(module_name: str) -> str:
    """返回模块的接口/后台/konfi 关联上下文（未命中返回空串）。"""
    if not module_name:
        return ""
    data = _load()
    for m in data.get("user_modules", []):
        mod = str(m.get("module") or "")
        if module_name in mod or mod in module_name:
            lines = [f"### 关联基座：{mod}"]
            if m.get("page"):
                lines.append(f"- 生产页面：{m['page']}")
            if m.get("interfaces_raw"):
                lines.append(f"- 生产接口：{m['interfaces_raw']}")
            if m.get("backend"):
                lines.append(f"- 运营后台：{m['backend']}")
            if m.get("konfi"):
                lines.append(f"- konfi：{m['konfi']}")
            return "\n".join(lines)
    return ""


def baseline_stats() -> dict:
    data = _load()
    return {
        "user_modules": len(data.get("user_modules", [])),
        "admin_modules": len(data.get("admin_modules", [])),
        "konfi_links": len(data.get("konfi_links", [])),
        "interface_map": len(data.get("interface_map", [])),
    }