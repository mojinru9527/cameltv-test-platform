#!/usr/bin/env python3
"""Enforce backend Ruff/mypy ratchets on the full configured rule set.

The repository has substantial historical static-analysis debt. This script
tracks the existing findings by file/code/message and occurrence count, then
fails when any new occurrence appears. The baseline can only shrink
intentionally via --update.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "test-platform-v2" / "backend"
DEFAULT_BASELINE = BACKEND_ROOT / "quality-ratchet-baseline.json"
PLATFORM_KEY = "win32" if sys.platform.startswith("win") else "linux" if sys.platform.startswith("linux") else sys.platform
MYPY_ERROR = re.compile(r"^(.+):(\d+): error: (.*)$")
MYPY_CODE = re.compile(r"\[([a-zA-Z0-9_-]+)\]\s*$")


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _portable_path(filename: str) -> str:
    path = Path(filename)
    if not path.is_absolute():
        path = (BACKEND_ROOT / path).resolve()
    try:
        return path.relative_to(BACKEND_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _ruff_findings() -> Counter[str]:
    executable = shutil.which("ruff")
    if not executable:
        raise RuntimeError("ruff executable not found; install the pinned quality toolchain first")
    result = _run(
        [executable, "check", "app/", "--config", "pyproject.toml", "--output-format=json"],
        BACKEND_ROOT,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ruff returned non-JSON output (exit={result.returncode}): {result.stderr[:500]}") from exc
    return Counter(
        f"{_portable_path(item['filename'])}:{item['code']}:{item.get('message', '').strip()}"
        for item in payload
    )


def _mypy_findings() -> Counter[str]:
    result = _run(
        [sys.executable, "-m", "mypy", "app/", "--ignore-missing-imports", "--no-error-summary"],
        BACKEND_ROOT,
    )
    findings: Counter[str] = Counter()
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        match = MYPY_ERROR.match(line)
        if not match:
            continue
        filename, _row, message = match.groups()
        code_match = MYPY_CODE.search(message)
        code = code_match.group(1) if code_match else "unknown"
        findings[f"{_portable_path(filename)}:{code}:{message.strip()}"] += 1
    if result.returncode not in (0, 1):
        raise RuntimeError(f"mypy failed unexpectedly (exit={result.returncode}): {result.stderr[:500]}")
    return findings


def _collect() -> dict[str, dict[str, int]]:
    return {
        "ruff": dict(sorted(_ruff_findings().items())),
        "mypy": dict(sorted(_mypy_findings().items())),
    }


def _load_baseline(path: Path) -> dict[str, dict[str, int]]:
    if not path.exists():
        raise RuntimeError(f"baseline missing: {path}; run with --update")
    payload = json.loads(path.read_text(encoding="utf-8"))
    mypy_platforms = payload.get("mypyPlatforms")
    if isinstance(mypy_platforms, dict):
        mypy = mypy_platforms.get(PLATFORM_KEY, {})
    else:
        mypy = payload.get("mypy", {})
    return {"ruff": payload.get("ruff", {}), "mypy": mypy}


def _write_baseline(path: Path, current: dict[str, dict[str, int]]) -> None:
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    mypy_platforms = dict(existing.get("mypyPlatforms", {}))
    mypy_platforms[PLATFORM_KEY] = current["mypy"]
    payload = {
        "schema_version": 3,
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": "line-independent finding counts; no new Ruff/mypy occurrence is allowed",
        "counts": {
            "ruff": sum(current["ruff"].values()),
            "mypyPlatforms": {
                platform: sum(findings.values())
                for platform, findings in mypy_platforms.items()
            },
        },
        "ruff": current["ruff"],
        "mypyPlatforms": mypy_platforms,
        "mypy": mypy_platforms.get("win32", current["mypy"]),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    current = _collect()
    if args.update:
        _write_baseline(args.baseline, current)
        print(
            f"updated {args.baseline}: "
            f"ruff={sum(current['ruff'].values())} mypy={sum(current['mypy'].values())}"
        )
        return 0

    baseline = _load_baseline(args.baseline)
    failed = False
    for tool in ("ruff", "mypy"):
        keys = set(current[tool]) | set(baseline[tool])
        increases = {
            key: current[tool].get(key, 0) - baseline[tool].get(key, 0)
            for key in keys
            if current[tool].get(key, 0) > baseline[tool].get(key, 0)
        }
        decreases = {
            key: baseline[tool].get(key, 0) - current[tool].get(key, 0)
            for key in keys
            if baseline[tool].get(key, 0) > current[tool].get(key, 0)
        }
        print(
            f"{tool}: baseline={sum(baseline[tool].values())} "
            f"current={sum(current[tool].values())} increased_keys={len(increases)} "
            f"decreased_keys={len(decreases)}"
        )
        if increases:
            failed = True
            print(f"{tool} new occurrences:")
            for key, count in sorted(increases.items())[:50]:
                print(f"  +{count} {key}")
            if len(increases) > 50:
                print(f"  ... {len(increases) - 50} more keys")
    if failed:
        print("QUALITY_RATCHET=FAIL")
        return 1
    print("QUALITY_RATCHET=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
