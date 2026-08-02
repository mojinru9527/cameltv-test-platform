#!/usr/bin/env python3
"""Validate the CamelTv repository boundary manifest (repo-boundaries.json).

The manifest defines which path belongs to which future repository
(frontend / backend / ops-platform / shared / deprecated-v1). Ownership uses
longest-prefix-wins semantics, so a deeper path may override a parent
assignment (e.g. an ops-platform file living today under test-platform-v2/backend).

Modes:
  --check      Validate the manifest against the real repository. Exit codes:
               0 = clean, 1 = ownership violations, 2 = invalid manifest.
  --selftest   Run built-in scenarios against a temp directory. Exit 0/1.

This script is pure standard library (Python 3.10+). It uses `git ls-files`
when available so local untracked artifacts never cause false positives; the
fallback walker is only used when git is unavailable (e.g. selftest temp dirs).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
MANIFEST_NAME = "repo-boundaries.json"
MAX_VIOLATIONS_SHOWN = 50

# Directories that are never part of repo ownership checks (vendored/local).
SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".eslintcache",
    "backups",
    "data",
    "site-packages",
}
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db"}


class ManifestError(Exception):
    """The manifest itself is invalid (schema, duplicates, missing paths)."""


@dataclass(frozen=True)
class Assignment:
    repo: str
    prefix: str
    depth: int


def norm_path(path: str) -> str:
    """Normalize a path to forward-slash relative form without leading/trailing slashes."""
    return path.replace("\\", "/").strip("/")


def git_tracked_files(root: Path) -> list[str]:
    """Return tracked file paths (relative to root) via `git ls-files -z`."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "-c", "core.quotepath=false", "ls-files", "-z"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError(f"git ls-files failed under {root}: {exc}") from exc
    return [
        entry.decode("utf-8", errors="replace").replace("\\", "/")
        for entry in proc.stdout.split(b"\0")
        if entry
    ]


def walk_files(root: Path) -> Iterator[str]:
    """Fallback walker when git is unavailable (used by --selftest)."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for name in filenames:
            if name in SKIP_FILE_NAMES:
                continue
            yield os.path.relpath(os.path.join(dirpath, name), root).replace("\\", "/")


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"cannot read manifest {manifest_path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(
            f"schema_version must be {SCHEMA_VERSION}, got {data.get('schema_version')!r}"
        )
    repos = data.get("repositories")
    if not isinstance(repos, dict) or not repos:
        raise ManifestError("'repositories' must be a non-empty object")
    for repo, spec in repos.items():
        if not isinstance(spec, dict):
            raise ManifestError(f"repository {repo!r} spec must be an object")
        if not isinstance(spec.get("description"), str) or not spec["description"].strip():
            raise ManifestError(f"repository {repo!r} is missing a non-empty 'description'")
        paths = spec.get("paths")
        if not isinstance(paths, list) or not all(
            isinstance(p, str) and p.strip() for p in paths
        ):
            raise ManifestError(
                f"repository {repo!r} 'paths' must be a non-empty list of strings"
            )
        rules = spec.get("rules", [])
        if not isinstance(rules, list) or not all(isinstance(r, str) for r in rules):
            raise ManifestError(f"repository {repo!r} 'rules' must be a list of strings")
    return data


def build_assignments(data: dict[str, Any], root: Path) -> dict[str, Assignment]:
    """Index manifest paths; reject duplicates and paths that do not exist."""
    assignments: dict[str, Assignment] = {}
    for repo, spec in data["repositories"].items():
        for raw_path in spec["paths"]:
            rel = norm_path(raw_path)
            if not rel:
                raise ManifestError(f"repository {repo!r} contains an empty path")
            if not (root / rel).exists():
                raise ManifestError(
                    f"manifest path does not exist: {rel!r} (repository {repo!r})"
                )
            existing = assignments.get(rel)
            if existing is not None:
                raise ManifestError(
                    f"duplicate exact assignment for {rel!r}: "
                    f"{existing.repo!r} and {repo!r}"
                )
            assignments[rel] = Assignment(repo=repo, prefix=rel, depth=rel.count("/"))
    return assignments


def owner_for(assignments: dict[str, Assignment], rel: str) -> Assignment | None:
    """Longest-prefix-wins ownership lookup."""
    best: Assignment | None = None
    for prefix, assignment in assignments.items():
        if rel == prefix or rel.startswith(prefix + "/"):
            if best is None or assignment.depth > best.depth:
                best = assignment
    return best


def analyze(
    tracked: list[str], assignments: dict[str, Assignment]
) -> tuple[dict[str, int], list[str]]:
    counts: dict[str, int] = {}
    violations: list[str] = []
    for raw_rel in tracked:
        rel = norm_path(raw_rel)
        if not rel:
            continue
        if rel == MANIFEST_NAME:
            counts["shared"] = counts.get("shared", 0) + 1
            continue
        owner = owner_for(assignments, rel)
        if owner is None:
            violations.append(rel)
        else:
            counts[owner.repo] = counts.get(owner.repo, 0) + 1
    return counts, violations


def top_level_violations(tracked: list[str], assignments: dict[str, Assignment]) -> list[str]:
    """Every tracked top-level segment must be covered by the manifest."""
    segments = sorted({norm_path(rel).split("/", 1)[0] for rel in tracked if norm_path(rel)})
    return [
        seg
        for seg in segments
        if seg not in SKIP_DIR_NAMES
        and seg != MANIFEST_NAME
        and owner_for(assignments, seg) is None
    ]


def run_check(root: Path, manifest_path: Path) -> int:
    data = load_manifest(manifest_path)
    assignments = build_assignments(data, root)
    if (root / ".git").exists():
        tracked = git_tracked_files(root)
    else:
        tracked = list(walk_files(root))
    counts, violations = analyze(tracked, assignments)
    missing_top = top_level_violations(tracked, assignments)

    print(f"Manifest      : {manifest_path}")
    print(f"Repo root     : {root}")
    print(f"Tracked files : {len(tracked)}")
    print("Coverage by repository:")
    for repo, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {repo:<16} {count:>6}")

    all_violations = [f"[top-level] {seg}" for seg in missing_top] + [
        f"[unassigned] {rel}" for rel in violations
    ]
    if not all_violations:
        print("RESULT: PASS - every tracked path has an owner.")
        return 0
    print(f"RESULT: FAIL - {len(all_violations)} ownership violation(s):")
    for item in all_violations[:MAX_VIOLATIONS_SHOWN]:
        print(f"  {item}")
    if len(all_violations) > MAX_VIOLATIONS_SHOWN:
        print(f"  ... and {len(all_violations) - MAX_VIOLATIONS_SHOWN} more")
    return 1


def _write(root: Path, rel: str, content: str = "") -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def selftest() -> int:
    scenarios: list[tuple[str, dict[str, Any], list[str], int]] = [
        (
            "clean manifest",
            {"schema_version": 1, "repositories": {
                "repo1": {"description": "d", "paths": ["a"]},
                "repo2": {"description": "d", "paths": ["b"]},
            }},
            ["a/x.txt", "b/y.txt"],
            0,
        ),
        (
            "nested override",
            {"schema_version": 1, "repositories": {
                "repo1": {"description": "d", "paths": ["a"]},
                "repo2": {"description": "d", "paths": ["a/special.py"]},
            }},
            ["a/plain.txt", "a/special.py"],
            0,
        ),
        (
            "unassigned file",
            {"schema_version": 1, "repositories": {
                "repo1": {"description": "d", "paths": ["a"]},
            }},
            ["a/x.txt", "rogue.py"],
            1,
        ),
        (
            "unassigned top-level",
            {"schema_version": 1, "repositories": {
                "repo1": {"description": "d", "paths": ["a"]},
            }},
            ["a/x.txt", "newdir/y.txt"],
            1,
        ),
        (
            "duplicate exact path",
            {"schema_version": 1, "repositories": {
                "repo1": {"description": "d", "paths": ["a"]},
                "repo2": {"description": "d", "paths": ["a"]},
            }},
            ["a/x.txt"],
            2,
        ),
        (
            "missing manifest path",
            {"schema_version": 1, "repositories": {
                "repo1": {"description": "d", "paths": ["does-not-exist"]},
            }},
            ["a/x.txt"],
            2,
        ),
        (
            "wrong schema version",
            {"schema_version": 99, "repositories": {
                "repo1": {"description": "d", "paths": ["a"]},
            }},
            ["a/x.txt"],
            2,
        ),
    ]
    failures = 0
    with tempfile.TemporaryDirectory(prefix="repo-boundary-selftest-") as tmp:
        for name, manifest_data, files, expected_code in scenarios:
            root = Path(tmp) / name.replace(" ", "_")
            root.mkdir()
            manifest_path = root / MANIFEST_NAME
            manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
            for rel in files:
                _write(root, rel, "x")
            try:
                code = run_check(root, manifest_path)
            except ManifestError as exc:
                code = 2
                message = str(exc)
            else:
                message = "no error"
            ok = code == expected_code
            failures += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: exit={code} expected={expected_code} ({message})")
    if failures:
        print(f"SELFTEST: FAIL ({failures} scenario(s) failed)")
        return 1
    print("SELFTEST: PASS (7/7)")
    return 0


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / MANIFEST_NAME).exists():
            return candidate
    return current


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate CamelTv repository boundary manifest."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate manifest against the repo")
    mode.add_argument("--selftest", action="store_true", help="run built-in scenarios")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repository root (default: auto-detected)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=f"manifest path (default: <repo-root>/{MANIFEST_NAME})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.selftest:
        return selftest()
    root = args.repo_root or find_repo_root(Path(__file__).resolve().parent)
    manifest = args.manifest or root / MANIFEST_NAME
    try:
        return run_check(root, manifest)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
