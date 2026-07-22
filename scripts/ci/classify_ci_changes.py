from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


DOCUMENT_SUFFIXES = {".md", ".mdx"}
NEUTRAL_PREFIXES = (
    ".claude/",
    ".githooks/",
    "docs/",
    "scripts/ci/",
    "scripts/git/",
    "work-logs/",
    "产品需求/",
)
BACKEND_PREFIXES = (
    "lanhu-mcp/",
    "test-platform-v2/backend/",
)
FRONTEND_PREFIXES = ("test-platform-v2/frontend/",)
CROSS_CUTTING_PREFIXES = (
    ".github/workflows/",
    "deploy/",
    "test-platform-v2/deploy/",
)
BACKEND_EXACT = {".gitmodules", "lanhu-mcp"}
CROSS_CUTTING_EXACT = {"Jenkinsfile"}


@dataclass(frozen=True)
class Classification:
    backend: bool
    frontend: bool
    reasons: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "frontend": self.frontend,
            "reasons": list(self.reasons),
        }


def _normalize(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _starts_with(path: str, prefixes: Sequence[str]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def classify_paths(paths: Iterable[str], force_all: bool = False) -> Classification:
    normalized_paths = tuple(path for path in (_normalize(raw) for raw in paths) if path)
    if force_all:
        return Classification(True, True, ("force-all",))
    if not normalized_paths:
        return Classification(True, True, ("empty-file-set",))

    backend = False
    frontend = False
    reasons: set[str] = set()

    for path in normalized_paths:
        suffix = Path(path).suffix.lower()
        if suffix in DOCUMENT_SUFFIXES:
            reasons.add("documentation")
        elif path in BACKEND_EXACT or _starts_with(path, BACKEND_PREFIXES):
            backend = True
            reasons.add("backend")
        elif _starts_with(path, FRONTEND_PREFIXES):
            frontend = True
            reasons.add("frontend")
        elif path in CROSS_CUTTING_EXACT or _starts_with(path, CROSS_CUTTING_PREFIXES):
            backend = True
            frontend = True
            reasons.add("cross-cutting")
        elif _starts_with(path, NEUTRAL_PREFIXES):
            reasons.add("governance")
        else:
            backend = True
            frontend = True
            reasons.add("unknown-fail-safe")

    return Classification(backend, frontend, tuple(sorted(reasons)))


def _read_paths(path: Path, null_delimited: bool) -> list[str]:
    data = path.read_bytes()
    chunks = data.split(b"\0") if null_delimited else data.splitlines()
    return [chunk.decode("utf-8", errors="surrogateescape") for chunk in chunks if chunk]


def _write_github_output(path: Path, result: Classification) -> None:
    reason = ",".join(result.reasons)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(f"backend={str(result.backend).lower()}\n")
        output.write(f"frontend={str(result.frontend).lower()}\n")
        output.write(f"reason={reason}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify CamelTv CI impact by changed path.")
    parser.add_argument("paths", nargs="*", help="Changed repository paths.")
    parser.add_argument("--files-from", type=Path, help="Read changed paths from a file.")
    parser.add_argument("--null", action="store_true", help="Use NUL-delimited --files-from input.")
    parser.add_argument("--force-all", action="store_true", help="Force backend and frontend checks.")
    parser.add_argument("--github-output", type=Path, help="Append outputs for GitHub Actions.")
    args = parser.parse_args(argv)

    paths = list(args.paths)
    if args.files_from:
        paths.extend(_read_paths(args.files_from, args.null))

    result = classify_paths(paths, force_all=args.force_all)
    if args.github_output:
        _write_github_output(args.github_output, result)
    print(json.dumps(result.as_json(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
