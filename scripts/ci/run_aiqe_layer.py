"""V16-022：AIQE 测试分层执行器（本地/CI 同一命令，输出 JUnit）。

层：
- unit：AIQE 单测（排除 browser/device/e2e）
- integration：tests/e2e/aiqe（真实 API/Worker/Driver 入口）
- browser：真实 Chromium 拦截/驱动
- device：设备/小程序/适配器
- security：安全负向（V16-001/002/003/004/012）
- migration：迁移单头/roundtrip（非 pytest，由 CI 脚本执行）
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "test-platform-v2" / "backend"
EXCLUDE_PARTS = ("playwright", "device", "miniapp", "testerarmy", "interception")

LAYERS: dict[str, list[str]] = {
    "unit": ["tests/test_aiqe_*.py"],
    "integration": ["tests/e2e/aiqe/test_*.py", "tests/e2e/aiqe/*.py"],
    "browser": [
        "tests/test_aiqe_v16_002_playwright_interception.py",
        "tests/test_aiqe_playwright_driver.py",
        "tests/test_aiqe_playwright_driver_v2.py",
    ],
    "device": [
        "tests/test_aiqe_ui_device_executor.py",
        "tests/test_aiqe_miniapp_adapter.py",
        "tests/test_aiqe_testerarmy_adapter.py",
    ],
    "security": [
        "tests/test_aiqe_v16_001_policy_fail_closed.py",
        "tests/test_aiqe_v16_002_playwright_interception.py",
        "tests/test_aiqe_v16_003_secret_handle_chain.py",
        "tests/test_aiqe_v16_004_query_registry_boundary.py",
        "tests/test_aiqe_v16_012_evidence_resolver.py",
    ],
}


def resolve_files(layer: str) -> list[str]:
    if layer not in LAYERS:
        raise KeyError(layer)
    files: list[str] = []
    for pattern in LAYERS[layer]:
        for match in sorted(glob.glob(str(BACKEND / pattern))):
            path = Path(match)
            if layer == "unit" and any(part in path.name for part in EXCLUDE_PARTS):
                continue
            relative = path.relative_to(BACKEND).as_posix()
            if relative not in files:
                files.append(relative)
    return files


def command_for(layer: str, junit: str | None) -> list[str]:
    files = resolve_files(layer)
    if not files:
        raise FileNotFoundError(f"layer {layer} 未匹配到测试文件")
    cmd = [sys.executable, "-m", "pytest", *files, "-q", "-p", "no:cacheprovider"]
    if junit:
        cmd.append(f"--junitxml={junit}")
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("layer", nargs="?")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--junit", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("pytest_args", nargs="*")
    args = parser.parse_args(argv)
    if args.list or not args.layer:
        for name in LAYERS:
            print(f"{name}: {len(resolve_files(name))} files")
        return 0 if args.list else 2
    try:
        cmd = command_for(args.layer, args.junit or None)
    except KeyError:
        print(f"::error::未知 layer: {args.layer}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2
    cmd.extend(args.pytest_args)
    print(" ".join(cmd))
    if args.dry_run:
        return 0
    import subprocess

    return subprocess.call(cmd, cwd=str(BACKEND))


if __name__ == "__main__":
    raise SystemExit(main())
