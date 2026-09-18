"""生成代码危险 API 静态拦截（Batch 259 / B2-2，H1 硬线）。

**边界声明（重要）**：本模块做的是**静态检查**，只能拦下"明显的"危险 API。
它不是沙箱——绕过方式很多（动态拼字符串、间接 require 等）。
真正的隔离由 `app/core/execution_sandbox.py`（环境白名单 + POSIX rlimit + 文件/网络收敛）
承担。两者缺一不可，不能互相替代；这一点与 B2-3 纠正的「dry-run 不是沙箱」是同一类问题。

拦截范围（09 方案 H1）：`child_process`、`fs` 写操作、`net`/`tls`/`dgram` 等直连、
以及 `process.env`（平台 E2E 契约变量 `CAMELTV_*` 除外）。
"""
from __future__ import annotations

import re


class SpecNotAllowedError(ValueError):
    """生成代码命中禁止使用的 API。"""


# (规则名, 正则, 可读原因)
_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "child_process",
        re.compile(r"\bchild_process\b"),
        "禁止在用例代码中使用 child_process（可在执行节点上直接运行任意命令）",
    ),
    (
        "process-spawn",
        re.compile(r"\b(?:execSync|spawnSync|execFileSync|execFile|spawn|exec)\s*\("),
        "禁止在用例代码中启动子进程（exec/spawn 家族）",
    ),
    (
        "fs-module",
        re.compile(r"""require\(\s*['"]fs(?:/promises)?['"]\s*\)|from\s+['"]fs(?:/promises)?['"]"""),
        "禁止在用例代码中直接引入 fs 模块（可读写节点文件系统）",
    ),
    (
        "fs-write",
        re.compile(
            r"\bfs\.(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|"
            r"unlink|unlinkSync|rm|rmSync|rmdir|rmdirSync|mkdir|mkdirSync|chmod|chmodSync)\b"
        ),
        "禁止在用例代码中写文件（用例只应通过浏览器/请求与被测系统交互）",
    ),
    (
        "raw-network",
        re.compile(r"""require\(\s*['"](?:net|tls|dgram|http|https|dns)['"]\s*\)"""),
        "禁止在用例代码中直接引入网络模块（应通过 page/request fixture 出网）",
    ),
    (
        "dynamic-eval",
        re.compile(r"\beval\s*\(|\bnew\s+Function\s*\("),
        "禁止在用例代码中动态求值（eval / new Function）",
    ),
    (
        "process-env",
        # 平台 E2E 契约变量 CAMELTV_* 放行（execution_sandbox 只保留该前缀）；
        # 其余环境变量（SECRET_KEY、数据库口令等）一律拒绝读取。
        re.compile(r"process\.env\.(?!CAMELTV_)[A-Za-z_][A-Za-z0-9_]*|process\.env\[\s*(?!['\"]CAMELTV_)"),
        "禁止在用例代码中读取平台环境变量（SECRET_KEY/数据库口令等只能留在控制面）",
    ),
)


def assert_spec_safe(code: str) -> list[str]:
    """返回命中的禁止项（含 1-based 行号）；空列表 = 通过。

    只报告、不抛异常：三条调用路径的错误文案不同（生成阶段提示 / 执行前拒绝），
    由调用方决定如何呈现，避免因为呈现方式不同而分裂成两份实现。
    """
    if not code:
        return []
    findings: list[str] = []
    for line_no, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("//") and "eslint" in stripped.lower():
            # eslint 指令注释不是可执行代码，避免误报
            continue
        for rule_name, pattern, reason in _RULES:
            if pattern.search(line):
                findings.append(f"第 {line_no} 行 [{rule_name}] {reason}")
    return findings


def raise_if_unsafe(code: str) -> None:
    """需要"拒绝执行"语义时的便捷包装。"""
    findings = assert_spec_safe(code)
    if findings:
        raise SpecNotAllowedError(
            "生成的用例代码包含禁止使用的 API，已拒绝执行：\n" + "\n".join(findings)
        )
