"""Batch 259 / B2-3 — 纠正「dry-run = 沙箱」的错误定位（含审计 S6 的表述部分）。

dry-run 只做语法/结构校验，**仍会执行 spec 顶层语句**，因此不是安全边界。
本文件把这条结论固化成可执行校验，避免"文档说不清、代码又默认按沙箱用"的老问题复发：
  1. 编译器模块里不允许出现 sandbox 字样（它不提供沙箱）；
  2. 任何文件都不允许把 sandbox 与 dry-run 写在同一行；
  3. `compile_to_playwright` 默认 `validate=True`，且计划执行路径不得显式关掉校验。
"""
from __future__ import annotations

import inspect
from pathlib import Path

import app
from app.services.case_compiler_service import compile_to_playwright

_APP_ROOT = Path(app.__file__).parent
_COMPILER = _APP_ROOT / "services" / "case_compiler_service.py"
_PLAN_SERVICE = _APP_ROOT / "services" / "test_plan_service.py"


def test_compiler_module_never_claims_a_sandbox():
    source = _COMPILER.read_text(encoding="utf-8", errors="replace").lower()
    offenders = [
        f"{line_no}: {line.strip()}"
        for line_no, line in enumerate(source.splitlines(), 1)
        # 允许引用真正的沙箱模块（execution_sandbox.py / spec_guard.py），
        # 但禁止本模块以任何其它方式声称自己提供了沙箱。
        if "sandbox" in line and "execution_sandbox" not in line
    ]
    assert offenders == [], (
        "case_compiler_service 只做语法校验，不提供沙箱，不得自称 sandbox: " f"{offenders}"
    )


def test_no_file_pairs_sandbox_with_dryrun():
    offenders: list[str] = []
    for path in _APP_ROOT.rglob("*.py"):
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            lowered = line.lower()
            if "sandbox" in lowered and ("dry-run" in lowered or "dry_run" in lowered):
                offenders.append(f"{path.relative_to(_APP_ROOT)}:{line_no}")
    assert offenders == [], f"仍把 dry-run 称作沙箱: {offenders}"


def test_compile_defaults_to_validation_on():
    default = inspect.signature(compile_to_playwright).parameters["validate"].default
    assert default is True, f"compile_to_playwright.validate 默认值应为 True，实际 {default!r}"


def test_plan_execution_path_does_not_disable_validation():
    source = _PLAN_SERVICE.read_text(encoding="utf-8", errors="replace")
    # 断言的是"实参写法"，因此注释里也不要出现该字面量——prose 同样会命中检查。
    forbidden = "validate" + "=False"
    assert forbidden not in source, (
        "计划执行路径不得跳过语法校验（审计 S6 的落点之一）；"
        "若确需跳过，必须在此处说明理由并同步本检查。"
    )
