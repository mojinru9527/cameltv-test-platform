"""M10-348：模拟 MQTT broker 契约验证（无实机）。

- 内置最小 MQTT 3.1.1 broker（CONNECT/SUBSCRIBE/PUBLISH/PING/DISCONNECT，QoS0）；
- paho 模拟设备：收到命令后发布遥测；
- IotDriver 通过真实 MQTT 协议读取遥测：只读守卫、断连失败、重连恢复。

用法：
  python scripts/qa/mqtt_sim_verify.py
退出码：0 = 全部通过；1 = 失败。
"""
from __future__ import annotations

import json
import queue
import socket
import struct
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test-platform-v2" / "backend"))

from app.aiqe.adapters.iot_driver import IotDriver  # noqa: E402

HOST = "127.0.0.1"
PORT = 18883
TOPIC_CMD = "aiqe/device/cmd"
TOPIC_TELEMETRY = "aiqe/device/telemetry"


def _read_packet(conn: socket.socket):
    header = conn.recv(1)
    if not header:
        return None
    first = header[0]
    multiplier = 1
    remaining = 0
    while True:
        byte = conn.recv(1)
        if not byte:
            return None
        digit = byte[0]
        remaining += (digit & 127) * multiplier
        if not digit & 128:
            break
        multiplier *= 128
    body = b""
    while len(body) < remaining:
        chunk = conn.recv(remaining - len(body))
        if not chunk:
            return None
        body += chunk
    return first, body


def _publish_packet(topic: str, payload: bytes) -> bytes:
    topic_bytes = topic.encode()
    body = struct.pack("!H", len(topic_bytes)) + topic_bytes + payload
    return bytes([0x30, len(body)]) + body


class MiniBroker:
    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self.host = host
        self.port = port
        self._stop = threading.Event()
        self._sock: socket.socket | None = None
        self._clients: dict[socket.socket, list[str]] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(8)
        self._sock.settimeout(0.2)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            clients = list(self._clients)
        for conn in clients:
            try:
                conn.close()
            except OSError:
                pass
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()  # type: ignore[union-attr]
            except (socket.timeout, OSError):
                continue
            with self._lock:
                self._clients[conn] = []
            threading.Thread(target=self._client_loop, args=(conn,), daemon=True).start()

    def _client_loop(self, conn: socket.socket) -> None:
        try:
            while not self._stop.is_set():
                packet = _read_packet(conn)
                if packet is None:
                    break
                first, body = packet
                ptype = first >> 4
                if ptype == 1:  # CONNECT
                    conn.sendall(bytes([0x20, 0x02, 0x00, 0x00]))
                elif ptype == 8:  # SUBSCRIBE
                    pid = body[:2]
                    filters = []
                    idx = 2
                    while idx < len(body):
                        length = struct.unpack("!H", body[idx : idx + 2])[0]
                        idx += 2
                        filters.append(body[idx : idx + length].decode())
                        idx += length + 1
                    with self._lock:
                        self._clients[conn].extend(filters)
                    conn.sendall(bytes([0x90, 2 + len(filters), *pid, *([0x00] * len(filters))]))
                elif ptype == 3:  # PUBLISH
                    length = struct.unpack("!H", body[:2])[0]
                    topic = body[2 : 2 + length].decode()
                    payload = body[2 + length :]
                    self._route(topic, payload)
                elif ptype == 12:  # PINGREQ
                    conn.sendall(bytes([0xD0, 0x00]))
        finally:
            with self._lock:
                self._clients.pop(conn, None)
            try:
                conn.close()
            except OSError:
                pass

    def _route(self, topic: str, payload: bytes) -> None:
        with self._lock:
            targets = [
                conn for conn, filters in self._clients.items() if any(self._matches(f, topic) for f in filters)
            ]
        for conn in targets:
            try:
                conn.sendall(_publish_packet(topic, payload))
            except OSError:
                pass

    @staticmethod
    def _matches(filt: str, topic: str) -> bool:
        if filt == topic or filt == "#":
            return True
        if "#" in filt:
            return topic.startswith(filt.split("#")[0])
        return False


class MqttTransport:
    def __init__(self) -> None:
        import paho.mqtt.client as mqtt

        self._queue: queue.Queue[bytes] = queue.Queue()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="aiqe-iot-driver")
        self.client.on_message = self._on_message
        self.client.connect(HOST, PORT, keepalive=5)
        self.client.subscribe(TOPIC_TELEMETRY)
        self.client.loop_start()

    def _on_message(self, client, userdata, message) -> None:
        self._queue.put(bytes(message.payload))

    def __call__(self, command: dict) -> dict:
        self.client.publish(TOPIC_CMD, json.dumps(command))
        try:
            payload = self._queue.get(timeout=2.0)
        except queue.Empty as exc:
            raise TimeoutError("遥测超时（broker 不可达或设备未响应）") from exc
        return json.loads(payload)

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()


class FakeDevice:
    def __init__(self) -> None:
        import paho.mqtt.client as mqtt

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="aiqe-sim-device")
        self.client.on_message = self._on_message
        self.client.connect(HOST, PORT, keepalive=5)
        self.client.subscribe(TOPIC_CMD)
        self.client.loop_start()

    def _on_message(self, client, userdata, message) -> None:
        command = json.loads(message.payload)
        telemetry = {"op": command.get("op"), "value": 42, "unit": "rpm"}
        self.client.publish(TOPIC_TELEMETRY, json.dumps(telemetry))

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()


def main() -> int:
    results: dict = {}
    broker = MiniBroker()
    broker.start()
    device = FakeDevice()
    transport = MqttTransport()
    driver = IotDriver("mqtt", transport)

    results["telemetry"] = driver.read_telemetry()

    try:
        driver.send({"op": "write"})
        results["readonly_guard"] = "FAILED: write allowed"
    except PermissionError as exc:
        results["readonly_guard"] = f"OK: {exc}"

    broker.stop()
    time.sleep(0.3)
    try:
        transport({"op": "telemetry"})
        results["disconnect"] = "FAILED: no timeout"
    except TimeoutError as exc:
        results["disconnect"] = f"OK: {exc}"

    broker = MiniBroker()
    broker.start()
    time.sleep(0.5)
    try:
        # 断连恢复：设备与驱动重新建连（真实设备重连语义）
        device.close()
        transport.close()
        device = FakeDevice()
        transport = MqttTransport()
        driver = IotDriver("mqtt", transport)
        results["reconnect"] = driver.read_telemetry()
    except Exception as exc:  # noqa: BLE001
        results["reconnect"] = f"FAILED: {type(exc).__name__}: {exc}"

    device.close()
    transport.close()
    broker.stop()
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    ok = (
        isinstance(results.get("telemetry"), dict)
        and results["telemetry"].get("value") == 42
        and str(results.get("readonly_guard", "")).startswith("OK")
        and str(results.get("disconnect", "")).startswith("OK")
        and isinstance(results.get("reconnect"), dict)
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
