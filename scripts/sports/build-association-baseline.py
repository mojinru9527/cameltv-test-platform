"""体育平台承接 — 知识中心关联基座生成（Batch 113，C112-1）。

解析 docs/体育平台-功能模块地图.md（v2）的模块/运营后台/konfi/接口映射表格，
与 evidence/batch-110 交叉校验（xhr-samples / konfi-inventory / admin nav / production-pages），
输出结构化关联基座 JSON（module→function→interface→backend→konfi），供知识中心入库与用例生成引用。

运行: <venv-python> scripts/sports/build-association-baseline.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = REPO_ROOT / "test-platform-v2" / "docs" / "体育平台-功能模块地图.md"
EVIDENCE = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110"
OUT_FILE = REPO_ROOT / "test-platform-v2" / "docs" / "体育平台-关联基座.json"
EVIDENCE_OUT = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-113"


def _load_json(rel: str):
    return json.loads((EVIDENCE / rel).read_text(encoding="utf-8"))


def _parse_table_rows(lines: list[str], start: int) -> list[list[str]]:
    """从 start 行开始解析 markdown 表格，返回去分隔行后的行列表（cell 去空白）。"""
    rows: list[list[str]] = []
    for line in lines[start:]:
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            break
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def _find_section(lines: list[str], key: str) -> int:
    for i, line in enumerate(lines):
        if line.startswith("## ") and key in line:
            return i + 1
    return -1


def _parse_interface_cell(cell: str) -> list[tuple[str, str]]:
    """解析接口单元格：'GET `/a`、`/b`、POST `/c`' → [(GET,/a),(GET,/b),(POST,/c)]。"""
    out: list[tuple[str, str]] = []
    cur_method = ""
    last_abs_dir = ""
    for seg in re.split(r"[、,，;；]", cell):
        seg = seg.strip()
        m = re.match(r"([A-Za-z]+)\s*`([^`]+)`", seg)
        if m:
            cur_method = m.group(1).upper()
            path = m.group(2).split("?")[0]
            if path.startswith("/"):
                last_abs_dir = str(Path(path).parent).replace("\\", "/")
            elif last_abs_dir:
                path = f"{last_abs_dir}/{path}"
            out.append((cur_method, path))
            continue
        m = re.match(r"`([^`]+)`", seg)
        if m and cur_method:
            path = m.group(1).split("?")[0]
            if path.startswith("/"):
                last_abs_dir = str(Path(path).parent).replace("\\", "/")
            elif last_abs_dir:
                path = f"{last_abs_dir}/{path}"
            out.append((cur_method, path))
    return out


def main() -> int:
    md = MAP_FILE.read_text(encoding="utf-8")
    lines = md.splitlines()
    issues: list[str] = []

    # ── §2 用户端功能模块矩阵 ──
    s2 = _find_section(lines, "用户端功能模块矩阵")
    user_modules = []
    if s2 >= 0:
        for cells in _parse_table_rows(lines, s2):
            if len(cells) < 5 or not cells[0]:
                continue
            if cells[0] in ("功能模块",) or cells[0].startswith("用户端/运营后台功能"):
                continue
            if cells[0].startswith("|"):
                cells = cells[1:]
            user_modules.append({
                "module": cells[0],
                "page": cells[1] if len(cells) > 1 else "",
                "interfaces_raw": cells[2] if len(cells) > 2 else "",
                "backend": cells[3] if len(cells) > 3 else "",
                "konfi": cells[4] if len(cells) > 4 else "",
            })

    # ── §3 运营后台功能模块矩阵 ──
    s3 = _find_section(lines, "运营后台功能模块矩阵")
    admin_modules = []
    if s3 >= 0:
        for cells in _parse_table_rows(lines, s3):
            if len(cells) < 4 or not cells[0]:
                continue
            if cells[0] in ("功能模块",):
                continue
            admin_modules.append({
                "module": cells[0],
                "pages": cells[1] if len(cells) > 1 else "",
                "requirement_pages": cells[2] if len(cells) > 2 else "",
                "case_domain": cells[3] if len(cells) > 3 else "",
                "status": cells[4] if len(cells) > 4 else "",
            })

    # ── §4 konfi 功能关联 ──
    s4 = _find_section(lines, "konfi 功能关联")
    konfi_links = []
    if s4 >= 0:
        for cells in _parse_table_rows(lines, s4):
            if len(cells) < 3 or not cells[0] or cells[0].startswith("用户端"):
                continue
            form_keys = re.findall(r"`([a-zA-Z0-9_]+)`", cells[1] if len(cells) > 1 else "")
            konfi_links.append({
                "function": cells[0],
                "form_keys": form_keys,
                "record_counts": cells[2] if len(cells) > 2 else "",
                "basis": cells[3] if len(cells) > 3 else "",
            })

    # ── §5 接口清单 ↔ 功能模块映射 ──
    s5 = _find_section(lines, "接口清单")
    interface_map = []
    if s5 >= 0:
        for cells in _parse_table_rows(lines, s5):
            if len(cells) < 3 or not cells[0] or cells[0].startswith("功能模块"):
                continue
            parsed = _parse_interface_cell(cells[1])
            if not parsed:
                issues.append(f"接口行无法解析: {cells[1]}")
                continue
            for method, path in parsed:
                interface_map.append({
                    "module": cells[0],
                    "method": method,
                    "path": path,
                    "sample_params": cells[2] if len(cells) > 2 else "",
                })

    # ── 交叉校验 ──
    samples = _load_json("xhr-samples/xhr-samples-final.json").get("samples", [])
    sample_paths_norm = {
        re.sub(r"^/[^/]+", "", (s.get("path") or "").split("?")[0])  # 去掉服务前缀
        for s in samples
    }
    missing_iface = []
    for i in interface_map:
        map_norm = re.sub(r"^/[^/]+", "", i["path"])
        if any(sp == map_norm or sp.endswith(map_norm) for sp in sample_paths_norm):
            continue
        missing_iface.append(i)
    if missing_iface:
        issues.append(f"接口不在 xhr-samples: {missing_iface}")

    konfi_inv = _load_json("konfi-inventory-sports.json")
    konfi_keys = {str(x.get("formKey")) for x in konfi_inv if x.get("formKey")}
    missing_konfi = sorted({k for link in konfi_links for k in link["form_keys"]} - konfi_keys)
    if missing_konfi:
        issues.append(f"formKey 不在 konfi-inventory: {missing_konfi}")

    nav = _load_json("admin-walkthrough/nav.json")
    nav_titles = {x.get("title") for x in (nav.get("items") or [])}
    nav_titles_norm = {str(t).split("（")[0].split("(")[0].strip() for t in nav_titles}
    missing_nav = [
        m["module"] for m in admin_modules
        if m["module"].split("（")[0].split("(")[0].strip() not in nav_titles_norm
    ]
    if missing_nav:
        issues.append(f"运营模块不在 nav 顶级菜单: {missing_nav}")

    pages = _load_json("production-walkthrough-v2/production-pages.json")
    page_urls = [p.get("url") or "" for p in (pages if isinstance(pages, list) else [])]
    if not page_urls:
        issues.append("production-pages 为空")

    baseline = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": ["docs/体育平台-功能模块地图.md (v2)", "evidence/batch-110/*"],
        "stats": {
            "user_modules": len(user_modules),
            "admin_modules": len(admin_modules),
            "konfi_links": len(konfi_links),
            "interface_map": len(interface_map),
            "production_pages": len(page_urls),
        },
        "user_modules": user_modules,
        "admin_modules": admin_modules,
        "konfi_links": konfi_links,
        "interface_map": interface_map,
    }
    OUT_FILE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")

    EVIDENCE_OUT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_OUT / "association-baseline-validation.json").write_text(
        json.dumps({
            "generated_at": baseline["generated_at"],
            "stats": baseline["stats"],
            "issues": issues,
            "valid": not issues,
            "sample_paths": len(sample_paths_norm),
            "konfi_keys": len(konfi_keys),
            "nav_titles": len(nav_titles),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[map] user={len(user_modules)} admin={len(admin_modules)} konfi={len(konfi_links)} iface={len(interface_map)} pages={len(page_urls)}")
    for x in issues:
        print(f"[issue] {x}")
    print(f"[out] {OUT_FILE.relative_to(REPO_ROOT)}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
