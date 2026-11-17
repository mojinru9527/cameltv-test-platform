"""Real Android Appium smoke via W3C touch pointer.

Usage:
  python scripts/qa/android_appium_smoke.py --udid 9f0564ba --package com.camelrn \
    --activity .MainActivity --tap-x 541 --tap-y 1615 --out work-logs/evidence/android

Requires a running Appium 2 server (APPIUM_URL, default http://127.0.0.1:4723)
and UiAutomator2. This performs a real touch tap, not a locator click.
"""
from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--appium-url", default="http://127.0.0.1:4723")
    parser.add_argument("--udid", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--activity", required=True)
    parser.add_argument("--tap-x", type=int, required=True)
    parser.add_argument("--tap-y", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    caps = {
        "capabilities": {
            "alwaysMatch": {
                "platformName": "Android",
                "appium:automationName": "UiAutomator2",
                "appium:udid": args.udid,
                "appium:appPackage": args.package,
                "appium:appActivity": args.activity,
                "appium:noReset": True,
                "appium:autoGrantPermissions": True,
                "appium:newCommandTimeout": 120,
            }
        }
    }
    with httpx.Client(timeout=120, trust_env=False) as client:
        response = client.post(f"{args.appium_url}/session", json=caps)
        response.raise_for_status()
        session_id = response.json()["value"]["sessionId"]
        base = f"{args.appium_url}/session/{session_id}"
        try:
            (out / "before.png").write_bytes(
                base64.b64decode(client.get(f"{base}/screenshot").json()["value"])
            )
            actions = {
                "actions": [
                    {
                        "type": "pointer",
                        "id": "finger1",
                        "parameters": {"pointerType": "touch"},
                        "actions": [
                            {"type": "pointerMove", "duration": 0, "x": args.tap_x, "y": args.tap_y},
                            {"type": "pointerDown", "button": 0},
                            {"type": "pause", "duration": 120},
                            {"type": "pointerUp", "button": 0},
                        ],
                    }
                ]
            }
            tap = client.post(f"{base}/actions", json=actions)
            tap.raise_for_status()
            time.sleep(4)
            (out / "after.png").write_bytes(
                base64.b64decode(client.get(f"{base}/screenshot").json()["value"])
            )
            (out / "after.xml").write_text(
                client.get(f"{base}/source").json()["value"], encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "session_id": session_id,
                        "tap": {"x": args.tap_x, "y": args.tap_y},
                        "out": str(out),
                    }
                )
            )
        finally:
            client.delete(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
