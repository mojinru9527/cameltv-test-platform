# -*- coding: utf-8 -*-
"""从蓝湖导出目录构建需求模块树（层级 + 设计稿截图清单）。

支持两种模式：
  * sitemap 模式（默认）：解析导出目录 data/document.js 的 sitemap 树（含 Folder/Wireframe
    层级与 url 字段），输出全量节点（含「新增/编辑」等子页面），lanhu_page_id 取 Wireframe 的 url。
  * enrich 模式（--enrich-existing）：用户端导出（document.js 为运营后台 sitemap 快照，不可用），
    保留既有 hierarchy.json 的层级归级，仅回填 screenshots（images/<页名>/ 下文件清单）。

用法：
    python scripts/build_lanhu_hierarchy.py ../data/lanhu-exports/运营后台原型
    python scripts/build_lanhu_hierarchy.py ../data/lanhu-exports/用户端原型 --enrich-existing

输出：<export_dir>/hierarchy.json（{path, type: module|page, lanhu_page_id, screenshots:[]}）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── sitemap 解析（document.js 为 minified JS 表达式树） ──────────────────────
def parse_sitemap(raw: str):
    """解析 _('rootNodes', [...]) 表达式，返回树对象。"""
    var_map = {}
    for m in re.finditer(r'([A-Za-z_$][A-Za-z0-9_$]*)=(?:"([^"]*)"|0x[0-9A-Fa-f]+|\d+)', raw):
        var_map[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(0).split("=")[1]
    idx = raw.find("_(r,[")
    if idx < 0:
        raise ValueError("sitemap rootNodes 起点 _(r,[ 未找到")
    pos = [idx]

    def parse_value():
        c = raw[pos[0]]
        if c == "_":
            pos[0] += 2
            obj = {}
            while raw[pos[0]] != ")":
                if raw[pos[0]] == ",":
                    pos[0] += 1
                if raw[pos[0]] == ")":
                    break
                m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", raw[pos[0]:])
                key = m.group(0)
                pos[0] += len(key)
                if raw[pos[0]] == ",":
                    pos[0] += 1
                obj[var_map.get(key, key)] = parse_value()
            pos[0] += 1
            return obj
        if c == "[":
            pos[0] += 1
            arr = []
            while raw[pos[0]] != "]":
                if raw[pos[0]] == ",":
                    pos[0] += 1
                if raw[pos[0]] == "]":
                    break
                arr.append(parse_value())
            pos[0] += 1
            return arr
        if c == '"':
            m = re.match(r'"([^"]*)"', raw[pos[0]:])
            pos[0] += len(m.group(0))
            return m.group(1)
        m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*|\d+", raw[pos[0]:])
        tok = m.group(0)
        pos[0] += len(tok)
        return var_map.get(tok, tok)

    return parse_value()


def _sanitize_segment(name: str) -> str:
    """蓝湖导出会把子页目录平铺为文件名：'新增/编辑广告活动' → '新增_编辑广告活动'。"""
    return name.replace("/", "_")


def build_from_sitemap(export_dir: Path) -> list[dict]:
    doc_js = export_dir / "data" / "document.js"
    cache = export_dir / ".lanhu_cache.json"
    root_name = "蓝湖导出"
    if cache.exists():
        try:
            root_name = json.loads(cache.read_text(encoding="utf-8")).get("document_name") or root_name
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            print(
                f"[build-hierarchy] 无法读取 {cache}，使用默认根名称：{exc}",
                file=sys.stderr,
            )
    tree = parse_sitemap(doc_js.read_text(encoding="utf-8", errors="ignore"))
    roots = tree.get("rootNodes", []) or []
    images_root = export_dir / "images"
    nodes: list[dict] = []

    def walk(items, segments):
        for n in items:
            page_name = n.get("pageName") or ""
            typ = n.get("type") or ""
            url = n.get("url") or ""
            children = n.get("children") or []
            if typ == "Folder":
                nodes.append(
                    {
                        "path": "/".join(segments + [page_name]),
                        "type": "module",
                        "lanhu_page_id": "",
                        "screenshots": [],
                    }
                )
                walk(children, segments + [page_name])
            else:
                seg = _sanitize_segment(page_name) if page_name else (url[: -len(".html")] if url else "")
                shots = []
                img_dir = images_root / (url[: -len(".html")] if url else seg)
                if img_dir.is_dir():
                    shots = sorted(f.name for f in img_dir.iterdir() if f.is_file())
                nodes.append(
                    {
                        "path": "/".join(segments + [seg]),
                        "type": "page",
                        "lanhu_page_id": url,
                        "screenshots": shots,
                    }
                )
                walk(children, segments + [seg])

    walk(roots, [root_name])
    return nodes


def enrich_existing(export_dir: Path) -> list[dict]:
    """保留既有 hierarchy.json 的归级，仅回填 screenshots。"""
    hier = export_dir / "hierarchy.json"
    if not hier.exists():
        raise FileNotFoundError(f"未找到 {hier}（enrich 模式需要既有 hierarchy.json）")
    nodes = json.loads(hier.read_text(encoding="utf-8"))
    images_root = export_dir / "images"
    for n in nodes:
        if n.get("type") != "page":
            n["screenshots"] = []
            continue
        pid = n.get("lanhu_page_id") or ""
        img_dir = images_root / (pid[: -len(".html")] if pid.endswith(".html") else pid)
        if img_dir.is_dir():
            n["screenshots"] = sorted(f.name for f in img_dir.iterdir() if f.is_file())
        else:
            n["screenshots"] = []
    return nodes


def main() -> int:
    ap = argparse.ArgumentParser(description="构建蓝湖需求模块树 hierarchy.json")
    ap.add_argument("export_dir", type=Path)
    ap.add_argument("--enrich-existing", action="store_true", help="保留既有 hierarchy.json 归级仅回填截图")
    args = ap.parse_args()

    export_dir: Path = args.export_dir.resolve()
    if not export_dir.is_dir():
        print(f"导出目录不存在: {export_dir}", file=sys.stderr)
        return 1

    if args.enrich_existing:
        nodes = enrich_existing(export_dir)
    else:
        nodes = build_from_sitemap(export_dir)

    out = export_dir / "hierarchy.json"
    out.write_text(json.dumps(nodes, ensure_ascii=False, indent=1), encoding="utf-8")
    pages = sum(1 for n in nodes if n["type"] == "page")
    modules = sum(1 for n in nodes if n["type"] == "module")
    shots = sum(len(n["screenshots"]) for n in nodes)
    print(f"{export_dir.name}: {len(nodes)} 节点（module {modules} / page {pages}），设计稿 {shots} 张 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
