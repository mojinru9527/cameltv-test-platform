"""真机性能验收采集驱动（Android 滚动场景 E2E，Batch 99）。

流程: 登录 → 取项目 → 创建设备会话 → start → 挂 WebSocket 采样流（同时 adb 驱动滚动）
      → stop → 报告/指标 → 冷启动测量 → 落盘证据 JSON。
运行: <venv-python> scripts/executor/run-real-device-acceptance.py --password <pw> [--backend-url ...]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

import httpx
import websockets


def adb_cmd(adb: str, device: str, *args: str) -> str:
    out = subprocess.run(
        [adb, "-s", device, *args], capture_output=True, text=True, timeout=30,
    )
    return out.stdout + out.stderr


def drive_scroll(adb: str, device: str, pkg: str, seconds: int) -> None:
    adb_cmd(adb, device, "shell", "am", "force-stop", pkg)
    adb_cmd(adb, device, "shell", "am", "start", "-n", f"{pkg}/.MainActivity")
    time.sleep(5)
    # 连续 fling：纵向赛事列表 + 横向 LIVE 轮播交替，保持帧持续产生
    end = time.time() + seconds
    i = 0
    while time.time() < end:
        if i % 2 == 0:
            adb_cmd(adb, device, "shell", "input", "swipe", "540", "1500", "540", "400", "300")
            time.sleep(0.3)
            adb_cmd(adb, device, "shell", "input", "swipe", "540", "400", "540", "1500", "300")
        else:
            adb_cmd(adb, device, "shell", "input", "swipe", "900", "900", "200", "900", "300")
            time.sleep(0.3)
            adb_cmd(adb, device, "shell", "input", "swipe", "200", "900", "900", "900", "300")
        time.sleep(0.4)
        i += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default="http://127.0.0.1:8046/api/v1")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", required=True)
    ap.add_argument("--adb", default=r"C:\Users\26029\AppData\Local\Android\Sdk\platform-tools\adb.exe")
    ap.add_argument("--device", default="dcd8891f")
    ap.add_argument("--pkg", default="com.camelrn")
    ap.add_argument("--drive-seconds", type=int, default=26)
    ap.add_argument("--output-dir", default="test-platform-v2/work-logs/evidence/batch-99")
    args = ap.parse_args()

    base = args.backend_url.rstrip("/")
    headers = {"X-Project-Id": "0", "Origin": "http://localhost:5216"}

    with httpx.Client(base_url=base, headers=headers, timeout=30) as client:
        login = client.post("/auth/login", json={"username": args.username, "password": args.password})
        login.raise_for_status()
        token = login.json()["data"]["access_token"]
        auth = {"Authorization": f"Bearer {token}", "X-Project-Id": "0", "Origin": "http://localhost:5216"}
        print("[login] ok", flush=True)

        projects = client.get("/projects", headers=auth).json()["data"]
        project_id = projects[0]["id"] if projects else None
        if not project_id:
            print("ERROR: no project available", flush=True)
            return 1
        auth["X-Project-Id"] = str(project_id)
        print(f"[project] using id={project_id}", flush=True)

        devs = client.get("/perf-sessions/devices", headers=auth).json()["data"]["devices"]
        dev = next((d for d in devs if d["device_id"] == args.device), None)
        if not dev:
            print(f"ERROR: device {args.device} not found: {devs}", flush=True)
            return 1
        print(f"[device] {dev['device_name']} / {dev['platform']} / {dev['os_version']} / {dev['status']}", flush=True)

        create = client.post("/perf-sessions", headers=auth, json={
            "device_id": args.device,
            "pkg_name": args.pkg,
            "metrics": ["cpu", "memory", "fps", "jank", "battery", "network"],
        }).json()["data"]
        sid, ssid = create["id"], create["session_id"]
        print(f"[session] created id={sid} session={ssid}", flush=True)

        client.post(f"/perf-sessions/{sid}/start", headers=auth).raise_for_status()
        print("[session] started", flush=True)

        ws_headers = {
            "Origin": "http://localhost:5216",
            "Authorization": f"Bearer {token}",
            "X-Project-Id": str(project_id),
        }
        ws_url = base.replace("http://", "ws://") + f"/perf-sessions/{sid}/stream"

        samples: list[dict] = []
        stop_ws = threading.Event()

        async def stream() -> None:
            async with websockets.connect(ws_url, additional_headers=ws_headers) as ws:
                while True:
                    try:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=40))
                    except asyncio.TimeoutError:
                        break
                    samples.append(msg)
                    if msg.get("type") in ("session_end", "error"):
                        break
                    if stop_ws.is_set() and msg.get("type") == "metrics_snapshot":
                        await ws.send(json.dumps({"action": "stop"}))
                        stop_ws.clear()

        import asyncio

        drive_thread = threading.Thread(
            target=drive_scroll, args=(args.adb, args.device, args.pkg, args.drive_seconds)
        )
        drive_thread.start()

        async def runner() -> None:
            task = asyncio.create_task(stream())
            while drive_thread.is_alive():
                await asyncio.sleep(1)
            stop_ws.set()
            await asyncio.sleep(2)
            await task

        asyncio.run(runner())
        print(f"[stream] samples={len(samples)}", flush=True)

        report = client.get(f"/perf-sessions/{sid}/report", headers=auth).json()["data"]
        for m in report.get("metrics", []):
            print(
                f"[metric] {m['metric_type']} samples={m['samples']} mean={m['mean']} "
                f"min={m['min_val']} max={m['max_val']} passed={m['passed']}",
                flush=True,
            )
        metrics = client.get(f"/perf-sessions/{sid}/metrics", headers=auth).json()["data"]
        print(f"[metrics] total_points={metrics['total_points']}", flush=True)

        adb_cmd(args.adb, args.device, "shell", "am", "force-stop", args.pkg)
        time.sleep(2)
        startup_raw = adb_cmd(args.adb, args.device, "shell", "am", "start", "-W", "-n", f"{args.pkg}/.MainActivity")
        total_time = 0
        import re
        m = re.search(r"TotalTime:\s*(\d+)", startup_raw)
        if m:
            total_time = int(m.group(1))
        print(f"[startup] TotalTime={total_time}ms", flush=True)

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        evidence = {
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "device": dev,
            "session": create,
            "stream_messages": samples,
            "total_points": metrics["total_points"],
            "report": report,
            "startup_ms": total_time,
            "startup_raw": startup_raw,
        }
        evidence_path = out_dir / "real-device-collection-batch99.json"
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[evidence] saved: {evidence_path}", flush=True)
        print(f"SESSION={ssid} ID={sid}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
