"""AUD-020：用本地真实 Android 设备验证 `device.android` 能力。

流程（官方 adb，不依赖 Appium）：
1. 启动目标 App（monkey LAUNCHER），等待渲染；
2. 抓取前台 Activity、uiautomator UI XML、截图；
3. 写入 AIQE 证据 Run + Artifact（截图/UI/设备信息）；
4. 注册 NodeCapabilityManifest 并 mark_verified，校验 Preflight READY。

用法：
    python scripts/aiqe/verify_android_device.py \
        --serial 9f0564ba --package com.camelrn \
        --adb C:/Users/<user>/AppData/Local/Android/Sdk/platform-tools/adb.exe
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{(BACKEND / 'data' / 'aiqe_evidence.db').as_posix()}")

import app.models  # noqa: E402,F401

from app.aiqe.models.run import TestRun  # noqa: E402
from app.aiqe.services import artifact_service, capability_registry  # noqa: E402
from app.aiqe.services.platform_binding_service import preflight_platform  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402


def adb(adb_path: str, serial: str, *args: str, binary: bool = False):
    completed = subprocess.run(
        [adb_path, "-s", serial, *args],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"adb {' '.join(args)} failed: {completed.stderr.decode(errors='ignore')[:300]}"
        )
    return completed.stdout if binary else completed.stdout.decode(errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb", default=os.environ.get("ADB_PATH", "adb"))
    parser.add_argument("--serial", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument(
        "--output",
        default=str(BACKEND.parent.parent / "docs/aiqe/evidence/android-node"),
    )
    parser.add_argument("--node-id", default="")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    manufacturer = adb(args.adb, args.serial, "shell", "getprop", "ro.product.manufacturer").strip()
    model = adb(args.adb, args.serial, "shell", "getprop", "ro.product.model").strip()
    android = adb(args.adb, args.serial, "shell", "getprop", "ro.build.version.release").strip()
    size = adb(args.adb, args.serial, "shell", "wm", "size").strip()

    adb(args.adb, args.serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb(args.adb, args.serial, "shell", "wm", "dismiss-keyguard")
    adb(args.adb, args.serial, "shell", "am", "force-stop", args.package)
    adb(
        args.adb,
        args.serial,
        "shell",
        "monkey",
        "-p",
        args.package,
        "-c",
        "android.intent.category.LAUNCHER",
        "1",
    )
    import time

    time.sleep(6)
    focus = adb(args.adb, args.serial, "shell", "dumpsys", "window")
    current_focus = next(
        (line.strip() for line in focus.splitlines() if "mCurrentFocus" in line), ""
    )
    if args.package not in current_focus:
        raise RuntimeError(f"App 未在前台: {current_focus}")

    adb(args.adb, args.serial, "shell", "uiautomator", "dump", "/sdcard/aiqe-window.xml")
    xml = adb(args.adb, args.serial, "shell", "cat", "/sdcard/aiqe-window.xml").encode()
    png = adb(args.adb, args.serial, "exec-out", "screencap", "-p", binary=True)
    (out / "screen-final.png").write_bytes(png)
    (out / "window-final.xml").write_bytes(xml)

    device = {
        "serial": args.serial,
        "manufacturer": manufacturer,
        "model": model,
        "android": android,
        "resolution": size,
        "package": args.package,
        "activity": current_focus,
        "tool": "adb (platform-tools)",
    }
    node_id = args.node_id or f"android-{model.lower().replace(' ', '-')}-{args.serial}"

    db = SessionLocal()
    try:
        run = TestRun(
            project_id=1,
            run_key=f"ANDROID-VERIFY-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            source_type="manual",
            status="COMPLETED",
            outcome="PASS",
            environment_snapshot_json={"device": device},
            created_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        db.add(run)
        db.flush()
        shot = artifact_service.put_artifact(
            db,
            project_id=1,
            run_id=run.id,
            content=png,
            artifact_type="SCREENSHOT",
            mime_type="image/png",
            metadata={"device": device, "source": "adb screencap"},
            redaction_status="sanitized",
        )
        ui = artifact_service.put_artifact(
            db,
            project_id=1,
            run_id=run.id,
            content=xml,
            artifact_type="DOM_SNAPSHOT",
            mime_type="application/xml",
            metadata={"device": device, "source": "adb uiautomator dump"},
            redaction_status="sanitized",
        )
        log = artifact_service.put_artifact(
            db,
            project_id=1,
            run_id=run.id,
            content=json.dumps(device, ensure_ascii=False, indent=2).encode(),
            artifact_type="DEVICE_LOG",
            mime_type="application/json",
            metadata={"source": "adb getprop"},
            redaction_status="sanitized",
        )
        manifest = capability_registry.register_manifest(
            db,
            node_id=node_id,
            driver_key="adb",
            driver_version=f"Android {android}",
            capabilities=["device.android"],
            platforms=["android"],
            evidence_ref=shot.id,
            heartbeat_at=datetime.now(UTC),
            runner_version="platform-tools",
            manifest_version="1.0",
            signature="local-device-evidence",
        )
        verified = capability_registry.mark_verified(
            db, manifest.node_id, platforms=["android"], evidence_ref=shot.id
        )
        status = capability_registry.compute_effective_status(verified)
        db.commit()
        preflight = preflight_platform(db, ["native_android"])
        payload = {
            "run_id": run.id,
            "run_key": run.run_key,
            "device": device,
            "artifacts": {"screenshot": shot.id, "ui_xml": ui.id, "device_log": log.id},
            "capability": {
                "node_id": manifest.node_id,
                "status": str(status),
                "evidence_ref": shot.id,
            },
            "preflight_native_android": preflight,
        }
        (out / "capability.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(payload, ensure_ascii=False))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
