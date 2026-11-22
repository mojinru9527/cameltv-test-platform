"""V1.6 迁移门禁：单头 + 可重跑 + 新迁移必须同时提供 upgrade/downgrade。

检查项：
1. `alembic/versions` 中 revision id 唯一、down_revision 都能解析到已有 revision；
2. 只有一个 head；
3. 每个迁移模块都定义了 `upgrade()` 与 `downgrade()`；
4. V1.6 新增迁移（`20261119_v16_*`）必须包含 inspect 守卫（可重跑）。

用法：python scripts/ci/check_aiqe_v16_migrations.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
VERSIONS = BACKEND / "alembic/versions"
V16_PREFIXES = ("20261119_v16_",)


def _parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    info = {"revision": None, "down_revision": None, "functions": set(), "source": text}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "revision":
                    info["revision"] = _constant_str(node.value)
                if target.id == "down_revision":
                    info["down_revision"] = _constant_value(node.value)
        if isinstance(node, ast.FunctionDef) and node.name in {"upgrade", "downgrade"}:
            info["functions"].add(node.name)
    return info


def _constant_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.AnnAssign):
        return _constant_str(node.value)
    return None


def _constant_value(node: ast.AST | None):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(
            element.value for element in node.elts if isinstance(element, ast.Constant)
        )
    return None


def main() -> int:
    errors: list[str] = []
    migrations: dict[str, dict] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        if path.name.startswith("__"):
            continue
        info = _parse(path)
        if not info["revision"]:
            errors.append(f"{path.name}: 缺少 revision")
            continue
        if info["revision"] in migrations:
            errors.append(f"{path.name}: revision 重复 {info['revision']}")
        migrations[info["revision"]] = info
        missing = {"upgrade", "downgrade"} - info["functions"]
        if missing:
            errors.append(f"{path.name}: 缺少函数 {sorted(missing)}")
        if path.name.startswith(V16_PREFIXES) and "inspect" not in info["source"]:
            errors.append(f"{path.name}: V1.6 新迁移必须是可重跑（inspect 守卫）")

    referenced: set[str] = set()
    for revision, info in migrations.items():
        down = info["down_revision"]
        if down is None:
            continue
        parents = down if isinstance(down, tuple) else (down,)
        for parent in parents:
            if parent not in migrations:
                errors.append(f"{revision}: down_revision 指向不存在的迁移 {parent}")
            referenced.add(parent)
    heads = sorted(set(migrations) - referenced)
    if len(heads) != 1:
        errors.append(f"必须只有一个 head，实际 {heads}")

    for error in errors:
        print(f"::error::[aiqe-v16-migrations] {error}")
    print(f"aiqe-v16 migrations: {len(migrations)} migrations, {len(heads)} head(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
