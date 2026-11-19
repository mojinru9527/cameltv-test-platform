"""真实 Android adb 冒烟：启动 App、校验前台 Activity、采集截图/UI 树。

供 AIQE `external_e2e` 节点在设备 Runner 上执行：
  python scripts/qa/android_adb_smoke.py --serial 9f0564ba --package com.camelrn --out <dir>

退出码：0=PASS / 1=FAIL（前台不是目标 App 或 adb 错误）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_ADB = os.environ.get(
    "ADB_PATH",
    r"C:\Users\26029\AppData\Local\Android\Sdk\platform-tools\adb.exe",
)


def adb(serial: str, *args: str, binary: bool = False):
    proc = subprocess.run(
        [DEFAULT_ADB, "-s", serial, *args],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"adb {' '.join(args)} failed: {proc.stderr.decode(errors='ignore')[:300]}"
        )
    return proc.stdout if binary else proc.stdout.decode(errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--wait-seconds", type=float, default=6.0)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = {"serial": args.serial, "package": args.package, "status": "FAIL"}
    try:
        model = adb(args.serial, "shell", "getprop", "ro.product.model").strip()
        android = adb(args.serial, "shell", "getprop", "ro.build.version.release").strip()
        adb(args.serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
        adb(args.serial, "shell", "wm", "dismiss-keyguard")
        adb(args.serial, "shell", "am", "force-stop", args.package)
        adb(
            args.serial,
            "shell",
            "monkey",
            "-p",
            args.package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        )
        time.sleep(max(1.0, args.wait_seconds))
        window = adb(args.serial, "shell", "dumpsys", "window")
        focus = next((line.strip() for line in window.splitlines() if "mCurrentFocus" in line), "")
        adb(args.serial, "shell", "uiautomator", "dump", "/sdcard/aiqe-smoke.xml")
        xml = adb(args.serial, "shell", "cat", "/sdcard/aiqe-smoke.xml").encode()
        png = adb(args.serial, "exec-out", "screencap", "-p", binary=True)
        (out / "screen.png").write_bytes(png)
        (out / "window.xml").write_bytes(xml)
        passed = args.package in focus
        result.update(
            {
                "model": model,
                "android": android,
                "focus": focus,
                "status": "PASS" if passed else "FAIL",
            }
        )
        (out / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if passed else 1
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
        (out / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
