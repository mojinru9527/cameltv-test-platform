"""Android Appium + cloud MQTT real-device E2E for AIQE external_e2e node.

Requires:
  - Appium 2 server at APPIUM_URL (default http://127.0.0.1:4723)
  - UiAutomator2 driver and a connected Android device
  - MQTT_* env vars (host/port/user/password/topic), TLS enabled

Exit 0 only when both the real touch and MQTT publish/receive succeed.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import threading
import time
import uuid
from pathlib import Path

import httpx
import paho.mqtt.client as mqtt


def _appium(out: Path, args) -> dict:
    base = os.getenv("APPIUM_URL", "http://127.0.0.1:4723").rstrip("/")
    caps = {
        "capabilities": {
            "alwaysMatch": {
                "platformName": "Android",
                "appium:automationName": "UiAutomator2",
                "appium:udid": args.udid,
                "appium:deviceName": args.device_name,
                "appium:appPackage": args.package,
                "appium:appActivity": args.activity,
                "appium:noReset": True,
                "appium:autoGrantPermissions": True,
                "appium:newCommandTimeout": 120,
                "appium:androidInstallTimeout": 120000,
                "appium:uiautomator2ServerInstallTimeout": 120000,
                "appium:uiautomator2ServerLaunchTimeout": 90000,
                "appium:skipServerInstallation": True,
            }
        }
    }
    with httpx.Client(timeout=300, trust_env=False) as client:
        created = client.post(base + "/session", json=caps)
        created.raise_for_status()
        sid = created.json()["value"]["sessionId"]
        endpoint = f"{base}/session/{sid}"
        try:
            before = client.get(endpoint + "/screenshot").json()["value"]
            (out / "android-before.png").write_bytes(base64.b64decode(before))
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
            client.post(endpoint + "/actions", json=actions).raise_for_status()
            time.sleep(4)
            after = client.get(endpoint + "/screenshot").json()["value"]
            (out / "android-after.png").write_bytes(base64.b64decode(after))
            source = client.get(endpoint + "/source").json()["value"]
            (out / "android-after.xml").write_text(source, encoding="utf-8")
            return {
                "ok": True,
                "session_id": sid,
                "tap": {"x": args.tap_x, "y": args.tap_y},
                "source_changed": before != after,
            }
        finally:
            client.delete(endpoint)


def _mqtt(out: Path) -> dict:
    host = os.environ["MQTT_HOST"]
    port = int(os.getenv("MQTT_PORT", "8883"))
    user = os.getenv("MQTT_USERNAME", "")
    password = os.getenv("MQTT_PASSWORD", "")
    topic = os.getenv("MQTT_TOPIC_TELEMETRY", "camel/aiqe/m6/telemetry")
    payload = json.dumps(
        {"op": "telemetry", "value": 42, "unit": "rpm", "source": "aiqe-android-e2e"}
    )
    state = {"connected": False, "subscribed": False, "messages": []}
    ready = threading.Event()
    received = threading.Event()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            state["connected"] = True
            client.subscribe(topic, qos=1)

    def on_subscribe(client, userdata, mid, rcs, properties=None):
        state["subscribed"] = True
        ready.set()

    def on_message(client, userdata, msg):
        state["messages"].append(
            {"topic": msg.topic, "payload": msg.payload.decode(errors="replace"), "qos": msg.qos}
        )
        received.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"aiqe-android-{uuid.uuid4().hex[:8]}")
    if user:
        client.username_pw_set(user, password)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    try:
        client.connect(host, port, 30)
        client.loop_start()
        if not ready.wait(15):
            return {"ok": False, "reason": "mqtt_subscribe_timeout", "state": state}
        info = client.publish(topic, payload, qos=1)
        info.wait_for_publish(timeout=10)
        ok = received.wait(10)
        result = {
            "ok": bool(ok),
            "host": host,
            "port": port,
            "topic": topic,
            "published": payload,
            "messages_received": len(state["messages"]),
            "messages": state["messages"],
        }
        (out / "mqtt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    finally:
        client.loop_stop()
        client.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--udid", default=os.getenv("ANDROID_UDID", ""))
    parser.add_argument("--device-name", default=os.getenv("ANDROID_DEVICE_NAME", "android"))
    parser.add_argument("--package", default=os.getenv("CAMELTV_ANDROID_PACKAGE", "com.camelrn"))
    parser.add_argument("--activity", default=os.getenv("CAMELTV_ANDROID_ACTIVITY", ".MainActivity"))
    parser.add_argument("--tap-x", type=int, default=541)
    parser.add_argument("--tap-y", type=int, default=1615)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = {"appium": None, "mqtt": None, "result": "FAIL"}
    try:
        result["appium"] = _appium(out, args)
        result["mqtt"] = _mqtt(out)
        if result["appium"].get("ok") and result["mqtt"].get("ok"):
            result["result"] = "PASS"
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": result["result"], "out": str(out)}))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
