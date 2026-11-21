"""V16-001/002 静态门禁：禁止 legacy fail-open 与无策略执行入口回归。

检查项（任一命中即非 0 退出）：
1. `app/aiqe/` 内不得出现 `_has_target_policy`、`_execute_http(`、`_execute_db(`；
2. `execute_inprocess_job` 不得使用 `policy_ctx = db if ...` 或 `db=None` 兼容开关；
3. `app/` 内对 `execute_node(...)` 的调用必须显式传 `policy_context=`（AST）；
4. `PlaywrightDriver(...)` 构造必须显式传 `policy=`（AST）；
5. `app/` 内不得 import `scripts.aiqe.migrate_workflow_target_policy`（迁移工具不得进入 Worker）。

用法：python scripts/ci/check_aiqe_v16_static_gates.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "test-platform-v2/backend"
AIQE = BACKEND / "app/aiqe"
APP = BACKEND / "app"

BANNED_LITERALS = (
    "_has_target_policy",
    "_execute_http(",
    "_execute_db(",
    "policy_ctx = db if",
    "unexpected keyword argument 'db'",
)
BANNED_IMPORTS = ("migrate_workflow_target_policy",)


def _iter_python(root: Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def check_literals(errors: list[str]) -> None:
    for path in _iter_python(AIQE):
        text = path.read_text(encoding="utf-8")
        for banned in BANNED_LITERALS:
            if banned in text:
                errors.append(f"{path.relative_to(REPO_ROOT)}: 禁止的 legacy 模式 {banned!r}")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _keyword_names(call: ast.Call) -> set[str]:
    return {keyword.arg for keyword in call.keywords if keyword.arg}


def check_calls(errors: list[str]) -> None:
    for path in _iter_python(APP):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:  # pragma: no cover - 语法错误由 ruff 拦截
            errors.append(f"{path.relative_to(REPO_ROOT)}: 无法解析（{exc}）")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            if name == "execute_node" and "policy_context" not in _keyword_names(node):
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: execute_node 未显式传 policy_context"
                )
            if name == "PlaywrightDriver" and "policy" not in _keyword_names(node):
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: PlaywrightDriver 未显式传 policy"
                )
            if name in BANNED_IMPORTS:
                errors.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}: Worker 进程不得使用迁移工具")


def check_imports(errors: list[str]) -> None:
    for path in _iter_python(APP):
        text = path.read_text(encoding="utf-8")
        for banned in BANNED_IMPORTS:
            if f"import {banned}" in text or f"from {banned}" in text:
                errors.append(f"{path.relative_to(REPO_ROOT)}: 禁止 import {banned}")


def main() -> int:
    errors: list[str] = []
    check_literals(errors)
    check_calls(errors)
    check_imports(errors)
    for error in errors:
        print(f"::error::[aiqe-v16-static] {error}")
    print(f"aiqe-v16 static gates: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
