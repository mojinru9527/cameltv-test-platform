"""Xmind import/export service for test cases.

Xmind .xmind files are ZIP archives containing content.json.
This service handles both directions: export test cases to .xmind (downloadable)
and import .xmind to create/update test cases.
"""
from __future__ import annotations

import json
import zipfile
from io import BytesIO
from typing import Any


def cases_to_xmind_bytes(cases: list[dict], root_title: str = "测试用例") -> BytesIO:
    """Export test cases as a .xmind file (ZIP with content.json).

    Structure:
        root_title
        ├── domain
        │   ├── module
        │   │   ├── [P0] case title
        │   │   └── [P2] another case
    """
    # Build tree structure: {domain: {module: [cases]}}
    tree: dict[str, dict[str, list[dict]]] = {}
    for c in cases:
        domain = c.get("domain", "未分类") or "未分类"
        module = c.get("module", "通用") or "通用"
        tree.setdefault(domain, {}).setdefault(module, []).append(c)

    # Build Xmind content.json structure
    xmind_root: dict[str, Any] = {
        "id": "root",
        "title": root_title,
        "children": {"attached": []},
    }

    for domain, modules in tree.items():
        domain_node: dict[str, Any] = {
            "id": f"d_{domain}",
            "title": domain,
            "children": {"attached": []},
        }
        for module, cases_in_mod in modules.items():
            module_node: dict[str, Any] = {
                "id": f"m_{domain}_{module}",
                "title": module,
                "children": {"attached": []},
            }
            for c in cases_in_mod:
                title = f"[{c.get('priority', 'P2')}] {c.get('title', '')}"
                case_node: dict[str, Any] = {
                    "id": f"c_{c.get('id', '')}",
                    "title": title,
                    "notes": {"plain": {
                        "content": (
                            f"编号: {c.get('case_id', '')}\n"
                            f"类型: {c.get('case_type', 'manual')}\n"
                            f"前置条件: {c.get('preconditions', '')}\n"
                            f"步骤: {c.get('steps', '[]')}\n"
                            f"预期结果: {c.get('expected_result', '')}"
                        ),
                    }},
                }
                module_node["children"]["attached"].append(case_node)
            domain_node["children"]["attached"].append(module_node)
        xmind_root["children"]["attached"].append(domain_node)

    # Build content.json
    content = [xmind_root]

    # Write ZIP
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json", json.dumps(content, ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf


def xmind_bytes_to_cases(data: bytes | str) -> list[dict]:
    """Parse an Xmind .xmind file and extract test cases.

    Accepts either raw bytes or a file path (str).
    When a file path is provided, the ZIP is read directly from disk
    without loading the entire file into memory (P1-S6d).

    Expected structure: root → domain → module → case (with [P0] prefix).
    Returns a list of case dicts ready for creation.
    """
    cases: list[dict] = []

    if isinstance(data, str):
        # File path — zipfile reads directly from disk (P1-S6d)
        with zipfile.ZipFile(data) as zf:
            content_json = zf.read("content.json")
            content = json.loads(content_json)
    else:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            content_json = zf.read("content.json")
            content = json.loads(content_json)

    def _walk(node, domain="", module=""):
        title = node.get("title", "")
        children = (node.get("children", {}) or {}).get("attached", []) or []

        # Determine level: if we have children, descend; if leaf, it's a case
        if not children:
            # Leaf = a test case
            priority = "P2"
            case_title = title
            if title.startswith("[P") and "]" in title[:5]:
                bracket_end = title.index("]")
                priority = title[1:bracket_end]
                case_title = title[bracket_end + 1:].strip()
            # Parse notes for detail
            notes = (node.get("notes", {}) or {}).get("plain", {}) or {}
            note_content = notes.get("content", "")
            cases.append({
                "title": case_title,
                "domain": domain,
                "module": module or "通用",
                "priority": priority,
                "case_type": "manual",
                "preconditions": _extract_field(note_content, "前置条件"),
                "steps": _extract_field(note_content, "步骤") or "[]",
                "expected_result": _extract_field(note_content, "预期结果") or "",
            })
            return

        # Internal node: could be domain, module, or sub-module
        for child in children:
            child_title = child.get("title", "")
            child_children = (child.get("children", {}) or {}).get("attached", []) or []

            if child_children and any(
                (c.get("children", {}) or {}).get("attached") for c in child_children
            ):
                # Has grandchildren that also have children → this is a domain
                _walk(child, domain=child_title, module=module)
            elif child_children:
                # Has grandchildren that are leaves → this is a module
                for gc in child_children:
                    _walk(gc, domain=domain or "未分类", module=child_title)
            else:
                # No children → top-level case (uncommon but handle)
                priority = "P2"
                ct = child_title
                if child_title.startswith("[P") and "]" in child_title[:5]:
                    b_end = child_title.index("]")
                    priority = child_title[1:b_end]
                    ct = child_title[b_end + 1:].strip()
                cases.append({
                    "title": ct,
                    "domain": domain or "未分类",
                    "module": module or "通用",
                    "priority": priority,
                    "case_type": "manual",
                })

    for root_node in content:
        _walk(root_node)

    return cases


def _extract_field(text: str, field: str) -> str:
    """Extract a field value from note text. Format: 'field: value\\n'."""
    for line in text.split("\n"):
        if line.startswith(f"{field}:") or line.startswith(f"{field}："):
            return line.split(":", 1)[-1].split("：", 1)[-1].strip()
    return ""
