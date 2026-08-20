"""Batch 181/182（FIX-173-P2-10 / C181-1）— 路由层禁 ORM 静态守卫。

规则（backend/CLAUDE.md 强制约定）：
1. api/v1 全部路由文件禁止 `from app.models import ...`（模型 import 清零）
2. 禁止 `select(` / `db.query(`（查询收敛 services）
3. `SessionLocal(` 豁免：BackgroundTasks/WebSocket 独立会话模式（defect/report/
   test_plan 等既有模式，仅指会话管理，不含查询）——本守卫不检查 SessionLocal
4. 路由文件体积上限 20KB（P2-10 验收）
"""
from __future__ import annotations

import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "app" / "api" / "v1"

_MODEL_IMPORT = re.compile(r"^\s*from\s+app\.models", re.M)
_ORM_CALL = re.compile(r"\b(select|db\.query)\s*\(")


def _scan_content(path: Path) -> str:
    """读取文件内容并剔除 `if TYPE_CHECKING:` 块（类型标注专用，非运行时 ORM 访问）。"""
    content = path.read_text(encoding="utf-8")
    # 简单块剔除：缩进 + `if TYPE_CHECKING:` 行，直到缩进回退
    out_lines = []
    in_type_checking = False
    checking_indent: int | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if not in_type_checking and stripped.startswith("if TYPE_CHECKING:"):
            in_type_checking = True
            checking_indent = len(line) - len(line.lstrip())
            continue
        if in_type_checking:
            indent = len(line) - len(line.lstrip())
            if stripped and indent <= checking_indent:
                in_type_checking = False
            else:
                continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _route_files() -> list[Path]:
    return sorted(p for p in API_DIR.glob("*.py") if p.name not in ("__init__.py",))


def test_no_model_imports_in_routes():
    violations = []
    for f in _route_files():
        content = _scan_content(f)
        if _MODEL_IMPORT.search(content):
            violations.append(f.name)
    assert violations == [], f"路由层禁止模型 import: {violations}"


def test_no_orm_calls_in_routes():
    violations = []
    for f in _route_files():
        content = _scan_content(f)
        for m in _ORM_CALL.finditer(content):
            violations.append(f"{f.name}:{content[:m.start()].count(chr(10)) + 1} {m.group(0)}")
    assert violations == [], f"路由层禁止 ORM 直连: {violations}"


def test_route_files_under_20kb():
    """P2-10 验收：api/v1 下不再有 >20KB 路由文件。"""
    big = [
        (p.name, p.stat().st_size // 1024)
        for p in API_DIR.glob("*.py")
        if p.stat().st_size > 20 * 1024
    ]
    assert big == [], f">20KB 路由文件仍存在: {big}"
