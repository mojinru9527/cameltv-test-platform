"""迁移 PG 布尔默认值静态守卫（hotfix 回归防护）。

事故背景：迁移中 `sa.Boolean() + server_default=sa.text("0"/"1")` 在
SQLAlchemy 2.0.51（requirements.lock 锁定版，生产 Docker 实际运行版本）下
被原样渲染为 `BOOLEAN DEFAULT 0/1`，PostgreSQL 严格拒绝
（DatatypeMismatch: boolean vs integer），导致生产启动迁移失败。
SQLite 宽松接受，CI 用未锁定 requirements.txt（2.0.52 已纠正渲染）会漏检。

本测试静态扫描全部迁移文件，禁止该写法复现；正确写法为
`server_default=sa.false()` / `sa.true()`（仓库现行惯例）。
"""
from __future__ import annotations

import re
from pathlib import Path

VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"

_BAD_DEFAULT_RE = re.compile(r'server_default\s*=\s*sa\.text\(\s*[\'"]0[\'"]\s*\)|server_default\s*=\s*sa\.text\(\s*[\'"]1[\'"]\s*\)')


def _column_blocks(source: str) -> list[str]:
    """提取所有 sa.Column(...) 调用的完整文本（括号平衡，支持跨行）。"""
    blocks: list[str] = []
    for m in re.finditer(r"sa\.Column\(", source):
        depth = 0
        start = m.start()
        i = m.end() - 1  # 从 '(' 开始计
        while i < len(source):
            ch = source[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start : i + 1])
                    break
            i += 1
    return blocks


def test_no_boolean_text_integer_server_default() -> None:
    offenders: list[str] = []
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for block in _column_blocks(source):
            if "sa.Boolean()" in block and _BAD_DEFAULT_RE.search(block):
                offenders.append(f"{path.name}: {block[:120]}")
    assert not offenders, (
        "迁移中发现 Boolean + sa.text(\"0\"/\"1\") server_default（PG 拒绝整数布尔默认值），"
        "请改用 sa.false()/sa.true()：\n" + "\n".join(offenders)
    )
