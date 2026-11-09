"""List Alembic heads (revision files not referenced by any down_revision).

Usage: python scripts/ci/alembic_heads.py <alembic/versions dir>
Prints one head per line; exit 2 if the directory is missing/unreadable.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:  # noqa: BLE001 - non-literal revision values are unsupported
        return None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: alembic_heads.py <versions dir>", file=sys.stderr)
        return 2
    versions = Path(sys.argv[1])
    if not versions.is_dir():
        print(f"versions dir not found: {versions}", file=sys.stderr)
        return 2
    revisions: dict[str, str] = {}
    downs: set[str] = set()
    for path in sorted(versions.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rev = None
        down = None
        for node in tree.body:
            targets: list[str] = []
            value = None
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
                value = node.value
            if not targets or value is None:
                continue
            if "revision" in targets:
                rev = literal(value)
            if "down_revision" in targets:
                down = literal(value)
        if not isinstance(rev, str) or not rev:
            continue
        revisions[rev] = path.name
        if isinstance(down, str):
            downs.add(down)
        elif isinstance(down, (tuple, list)):
            downs.update(str(x) for x in down if x)
    heads = sorted(r for r in revisions if r not in downs)
    for head in heads:
        print(head)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
