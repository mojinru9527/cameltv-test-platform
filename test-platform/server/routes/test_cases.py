"""测试用例管理 REST API — CRUD + 导入。"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.store import (
    list_cases, get_case, create_case, update_case, delete_case, list_modules, _connect,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 测试用例可能在 test-platform 同级或上级目录
_GENERATED_DIR = _PROJECT_ROOT / "tests" / "api-testing" / "generated"
_FUNCTIONAL_DIR = _PROJECT_ROOT / "tests" / "test-cases" / "functional"
_TEST_CASES_DIR = _PROJECT_ROOT / "tests" / "test-cases"

# 兜底：如果 tests/ 不直接在 test-platform 下，向上找
if not _TEST_CASES_DIR.exists():
    _alt = _PROJECT_ROOT.parent / "tests" / "test-cases"
    if _alt.exists():
        _TEST_CASES_DIR = _alt
        _FUNCTIONAL_DIR = _alt / "functional"
if not _GENERATED_DIR.exists():
    _alt = _PROJECT_ROOT.parent / "tests" / "api-testing" / "generated"
    if _alt.exists():
        _GENERATED_DIR = _alt

router = APIRouter(tags=["test-cases"])


# ── Request models ──────────────────────────────────────────────

class CaseCreate(BaseModel):
    title: str
    module: str = ""
    priority: str = "P2"
    status: str = "draft"
    type: str = "api"
    tags: list[str] = Field(default_factory=list)
    preconditions: str = ""
    steps: list[dict] = Field(default_factory=list)  # [{step, desc, expected}]
    expected_result: str = ""
    api_spec_ref: str = ""


class CaseUpdate(BaseModel):
    title: str | None = None
    module: str | None = None
    priority: str | None = None
    status: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    preconditions: str | None = None
    steps: list[dict] | None = None
    expected_result: str | None = None
    api_spec_ref: str | None = None


class CaseImport(BaseModel):
    """从 API 测试生成的 spec 导入用例。"""
    source: str = "api-test"
    cases: list[CaseCreate] = Field(default_factory=list)


# ── Routes ───────────────────────────────────────────────────────

@router.get("/test-cases")
def list_test_cases(
    module: str = "",
    priority: str = "",
    status: str = "",
    type: str = "",
    keyword: str = "",
    limit: int = 200,
    offset: int = 0,
):
    cases, total = list_cases(
        module=module, priority=priority, status=status, type=type,
        keyword=keyword, limit=limit, offset=offset,
    )
    return {"cases": cases, "total": total}


@router.get("/test-cases/modules")
def get_modules():
    return {"modules": list_modules()}


@router.get("/test-cases/{case_id}")
def get_test_case(case_id: int):
    case = get_case(case_id)
    if not case:
        raise HTTPException(404, "用例不存在")
    return case


@router.post("/test-cases")
def create_test_case(body: CaseCreate):
    data = body.model_dump()
    return create_case(data)


@router.put("/test-cases/{case_id}")
def update_test_case(case_id: int, body: CaseUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    case = update_case(case_id, data)
    if not case:
        raise HTTPException(404, "用例不存在")
    return case


@router.delete("/test-cases/{case_id}")
def delete_test_case(case_id: int):
    ok = delete_case(case_id)
    if not ok:
        raise HTTPException(404, "用例不存在")
    return {"deleted": True}


@router.post("/test-cases/import")
def import_test_cases(body: CaseImport):
    """批量从 API spec 导入用例到用例库。"""
    imported = []
    for c in body.cases:
        data = c.model_dump()
        data.setdefault("type", "api")
        data.setdefault("status", "active")
        imported.append(create_case(data))
    return {"imported": len(imported), "cases": imported}


# ═══════════════════════════════════════════════════════════════════
# 自动扫描导入 (functional .md + api .spec.ts)
# ═══════════════════════════════════════════════════════════════════


def _parse_md_table(content: str) -> list[dict]:
    """解析 Markdown 中的测试用例表格，返回 [{用例编号, 模块, 用例标题, ...}]。

    表格格式: | 用例编号 | 模块 | 用例标题 | 重要程度 | 前提条件 | 操作步骤 | 预期结果 | 备注 |
    """
    rows = []
    in_table = False
    header_parsed = False

    for line in content.split("\n"):
        stripped = line.strip()

        # 识别表格行（至少包含 6 个 | 分隔符）
        if not stripped.startswith("|") or not stripped.endswith("|"):
            in_table = False
            header_parsed = False
            continue

        cells = [c.strip() for c in stripped[1:-1].split("|")]

        # 跳过分隔行 (|---|---|)
        if all(re.match(r"^[-:]+$", c) for c in cells if c):
            if in_table:
                header_parsed = True
            continue

        # 识别表头
        if not in_table:
            first_cell = cells[0].lower() if cells else ""
            if "用例编号" in first_cell or "case" in first_cell:
                in_table = True
                continue
            # 也可能是直接的数据行（无表头标记）
            if re.match(r"^(TC-|API-TC-)", cells[0]) if cells else False:
                in_table = True
                header_parsed = True
            else:
                continue

        if not header_parsed:
            continue

        # 第一列必须是有效的用例编号
        if not cells or not re.match(r"^(TC-|API-TC-)", cells[0]):
            continue

        # 至少需要 7 个字段
        while len(cells) < 7:
            cells.append("")

        rows.append({
            "case_id": cells[0],
            "module": cells[1] if len(cells) > 1 else "",
            "title": cells[2] if len(cells) > 2 else "",
            "priority": cells[3] if len(cells) > 3 else "P2",
            "preconditions": cells[4] if len(cells) > 4 else "",
            "steps_raw": cells[5] if len(cells) > 5 else "",
            "expected": cells[6] if len(cells) > 6 else "",
            "notes": cells[7] if len(cells) > 7 else "",
        })
        in_table = True

    return rows


def _parse_steps(steps_raw: str) -> list[dict]:
    """将操作步骤文本拆分为结构化步骤列表。

    例: '1.登录<br>2.进入页面' → [{step:1, desc:'登录', expected:''}, ...]
    """
    if not steps_raw:
        return []
    # 按 <br> 或数字序号拆分
    parts = re.split(r"<br\s*/?>|\n|(?<!\d)(?=\d+\.)", steps_raw)
    steps = []
    seq = 1
    for p in parts:
        p = re.sub(r"^\d+[\.\、\)]\s*", "", p).strip()
        if p:
            steps.append({"step": seq, "desc": p, "expected": ""})
            seq += 1
    return steps


def _import_api_specs(existing_refs: set) -> dict:
    """导入 API 测试 .spec.ts 文件。"""
    imported = []
    skipped = 0
    files = 0

    if _GENERATED_DIR.exists():
        spec_files = sorted(_GENERATED_DIR.rglob("*.spec.ts"))
        files = len(spec_files)

        for spec_path in spec_files:
            rel = spec_path.relative_to(_GENERATED_DIR)
            module = rel.parts[0] if len(rel.parts) > 1 else "Default"

            content = spec_path.read_text(encoding="utf-8")

            endpoint = ""
            summary = ""
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("// endpoint:") and not endpoint:
                    endpoint = line.replace("// endpoint:", "").strip()
                if line.startswith("// summary:") and not summary:
                    summary = line.replace("// summary:", "").strip()
                if endpoint and summary:
                    break

            api_spec_ref = f"api-spec:{module}:{spec_path.stem}"
            if api_spec_ref in existing_refs:
                skipped += 1
                continue

            test_names = re.findall(r"test\('([^']+)',", content)
            if not test_names:
                test_names = re.findall(r'test\("([^"]+)",', content)

            steps = [
                {"step": i + 1, "desc": f"执行测试: {tn}", "expected": "通过"}
                for i, tn in enumerate(test_names)
            ]

            data = {
                "title": endpoint or spec_path.stem,
                "module": module,
                "priority": "P1",
                "status": "active",
                "type": "api",
                "tags": [module.lower(), "swagger", "auto-generated"],
                "preconditions": summary or "",
                "steps": steps,
                "expected_result": f"所有 {len(test_names)} 条测试用例通过",
                "api_spec_ref": api_spec_ref,
            }
            create_case(data)
            imported.append({"title": endpoint or spec_path.stem, "module": module, "test_count": len(test_names), "type": "api"})

    return {"imported": len(imported), "skipped": skipped, "files": files, "items": imported}


def _import_functional_md(existing_refs: set) -> dict:
    """导入 functional/*.md 和根级 .md 功能测试用例。"""
    imported = []
    skipped = 0
    files = 0

    # 收集所有要扫描的 md 文件
    md_files: list[Path] = []
    if _FUNCTIONAL_DIR.exists():
        md_files.extend(sorted(_FUNCTIONAL_DIR.glob("*.md")))
    if _TEST_CASES_DIR.exists():
        # 根级 md（如 体育平台最新版本-测试用例.md），排除 INDEX.md 和 README.md
        for p in sorted(_TEST_CASES_DIR.glob("*.md")):
            if p.name not in ("INDEX.md", "README.md") and p not in md_files:
                md_files.append(p)

    files = len(md_files)

    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8")
        rows = _parse_md_table(content)

        for row in rows:
            case_id = row["case_id"]
            api_spec_ref = f"functional:{md_path.stem}:{case_id}"

            if api_spec_ref in existing_refs:
                skipped += 1
                continue

            # 判断类型：API-TC- 开头为 api，否则为 manual
            case_type = "api" if case_id.startswith("API-TC-") else "manual"

            # 确定归属端：运营后台相关文件 / ADMIN 模块
            is_admin = "ADMIN" in md_path.stem.upper() or "运营后台" in md_path.stem or row["module"].startswith("ADMIN-") or "运营后台" in row["module"]

            tags = [row["module"].lower().replace(" ", "-"), "functional"]
            if is_admin:
                tags.append("运营后台")
            else:
                tags.append("用户端")

            # 规范化优先级
            priority = row["priority"].strip()
            if priority not in ("P0", "P1", "P2", "P3"):
                priority = "P2"

            data = {
                "title": f"[{case_id}] {row['title']}",
                "module": row["module"],
                "priority": priority,
                "status": "active",
                "type": case_type,
                "tags": tags,
                "preconditions": row["preconditions"],
                "steps": _parse_steps(row["steps_raw"]),
                "expected_result": row["expected"],
                "api_spec_ref": api_spec_ref,
            }
            create_case(data)
            imported.append({
                "case_id": case_id,
                "title": row["title"],
                "module": row["module"],
                "type": case_type,
                "priority": row["priority"],
            })

    return {"imported": len(imported), "skipped": skipped, "files": files, "items": imported}


@router.post("/test-cases/import-all")
def import_all_test_cases():
    """一键扫描并导入所有测试用例。

    来源:
      - tests/test-cases/functional/*.md    (功能用例)
      - tests/test-cases/*.md               (根级版本用例)
      - tests/api-testing/generated/**/*.spec.ts (API 接口用例)

    自动解析 Markdown 表格和 Playwright spec 文件，去重导入。
    """
    conn = _connect()
    existing_refs = set(
        row[0] for row in conn.execute("SELECT api_spec_ref FROM test_cases WHERE api_spec_ref != ''").fetchall()
    )
    conn.close()

    result_func = _import_functional_md(existing_refs)
    # 更新已导入 ref 防止跨来源重复
    existing_refs |= {f"functional:{item.get('case_id', '')}" for item in result_func["items"] if isinstance(item, dict)}

    result_api = _import_api_specs(existing_refs)

    return {
        "functional": {
            "imported": result_func["imported"],
            "skipped": result_func["skipped"],
            "files": result_func["files"],
        },
        "api_spec": {
            "imported": result_api["imported"],
            "skipped": result_api["skipped"],
            "files": result_api["files"],
        },
        "total_imported": result_func["imported"] + result_api["imported"],
        "total_skipped": result_func["skipped"] + result_api["skipped"],
        "samples": (result_func["items"][:5] if result_func["items"] else []) +
                   (result_api["items"][:3] if result_api["items"] else []),
    }
