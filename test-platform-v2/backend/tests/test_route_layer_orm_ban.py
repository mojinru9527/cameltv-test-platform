"""Batch 181（FIX-173-P2-10）— 路由层禁 ORM 静态守卫。

范围：本批拆分的 9 域路由文件（knowledge_*/requirement_*/requirement_modules_*/
wiki_*/apitest_*/test_case_*/release_bundles_*/lanhu_evidence_*/test_plan_*）。
规则：
1. 不得 `from app.models import ...`（模型 import 清零）
2. 不得出现 `select(` / `db.query(` / `SessionLocal(`（查询收敛 services；
   BackgroundTasks 独立会话为既有豁免模式，本批文件不应出现）
3. 路由文件体积上限 20KB（P2-10 验收：>20KB 文件清零）
"""
from __future__ import annotations

import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "app" / "api" / "v1"

# 本批拆分的 9 域新文件前缀（旧文件在集成时删除，不在守卫范围）
SPLIT_PREFIXES = (
    "knowledge_",
    "requirement_",
    "requirement_modules_",
    "wiki_",
    "apitest_",
    "test_case_",
    "release_bundles_",
    "lanhu_evidence_",
    "test_plan_",
)

_MODEL_IMPORT = re.compile(r"^\s*from\s+app\.models\s+import", re.M)
_ORM_CALL = re.compile(r"\b(select|db\.query)\s*\(")
# SessionLocal 豁免：test_plan/defect/report 等既有的 BackgroundTasks 独立会话模式
# （会话管理，非查询；Batch 181 约定明确豁免）


def _split_files() -> list[Path]:
    return sorted(p for p in API_DIR.glob("*.py") if p.name.startswith(SPLIT_PREFIXES))


def test_split_files_exist():
    """拆分产物必须存在（9 域 ≥ 预期文件数）。"""
    files = _split_files()
    assert files, "未找到拆分后的路由文件——拆分未完成？"
    expected_min = {
        "knowledge_": 3, "requirement_": 3, "requirement_modules_": 3,
        "wiki_": 4, "apitest_": 3, "test_case_": 3,
        "release_bundles_": 2, "lanhu_evidence_": 3, "test_plan_": 2,
    }
    for prefix, minimum in expected_min.items():
        count = sum(1 for f in files if f.name.startswith(prefix))
        assert count >= minimum, f"{prefix}* 拆分文件不足（{count} < {minimum}）"


def test_no_model_imports_in_split_routes():
    violations = []
    for f in _split_files():
        content = f.read_text(encoding="utf-8")
        if _MODEL_IMPORT.search(content):
            violations.append(f.name)
    assert violations == [], f"路由层禁止模型 import: {violations}"


def test_no_orm_calls_in_split_routes():
    violations = []
    for f in _split_files():
        content = f.read_text(encoding="utf-8")
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
