"""Real cloud MQTT TLS smoke (read-only by default).

Examples:
  python scripts/qa/mqtt_cloud_smoke.py --host HOST --username USER --topic camel/aiqe/m6/telemetry --listen-seconds 30
  python scripts/qa/mqtt_cloud_smoke.py ... --publish '{"op":"telemetry","value":42}'

Read-only mode never publishes. --publish is explicit and should only be used
when the broker credential is allowed to publish.
"""
from __future__ import annotations

import argparse
import json
import ssl
import threading
import time
import uuid

import paho.mqtt.client as mqtt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", default="")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--tls", action="store_true", default=True)
    parser.add_argument("--listen-seconds", type=float, default=10)
    parser.add_argument("--publish", default="", help="explicit test payload; empty = read-only")
    args = parser.parse_args()

    state = {
        "connected": False,
        "subscribed": False,
        "messages": [],
        "connect_reason": None,
        "subscribe_reason": None,
    }
    connected = threading.Event()
    subscribed = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        state["connect_reason"] = str(reason_code)
        if reason_code == 0:
            state["connected"] = True
            connected.set()
            client.subscribe(args.topic, qos=1)

    def on_subscribe(client, userdata, mid, reason_code_list, properties=None):
        state["subscribed"] = True
        state["subscribe_reason"] = str(reason_code_list)
        subscribed.set()

    def on_message(client, userdata, msg):
        state["messages"].append(
            {
                "topic": msg.topic,
                "payload": msg.payload.decode(errors="replace")[:1000],
                "qos": msg.qos,
            }
        )

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"aiqe-cloud-{uuid.uuid4().hex[:8]}",
    )
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    try:
        client.connect(args.host, args.port, keepalive=30)
        client.loop_start()
        ok = connected.wait(15)
        sub_ok = subscribed.wait(10) if ok else False
        published = None
        if args.publish and ok:
            info = client.publish(args.topic, args.publish, qos=1)
            info.wait_for_publish(timeout=10)
            published = {"topic": args.topic, "payload": args.publish, "qos": 1}
        time.sleep(max(0.0, args.listen_seconds))
        result = {
            "host": args.host,
            "port": args.port,
            "tls": args.tls,
            "username": args.username,
            "topic": args.topic,
            "connected": ok,
            "connect_reason": state["connect_reason"],
            "subscribed": sub_ok,
            "subscribe_reason": state["subscribe_reason"],
            "published": published,
            "messages_received": len(state["messages"]),
            "messages": state["messages"],
            "mode": "publish+subscribe" if args.publish else "read-only (no publish)",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok and sub_ok else 2
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
