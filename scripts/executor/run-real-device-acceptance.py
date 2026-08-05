"""真机性能验收采集驱动（Batch 99 双视频场景版）。

  场景（--scenario）:
  scroll        滚动压测（旧口径，仅作辅助数据）
  chrome-sports 安卓 Chrome 打开 www.camel1.tv，任选一场有视频流的比赛观看 10 分钟
  app-live      小象直播 App 任选一个视频流直播间观看 10 分钟
  manual        用户手动驱动目标应用/页面，平台仅按 duration 采样（广告/登录受限场景兜底）

流程: 登录 → 取项目 → 建会话 → start → WebSocket 采样（期间驱动目标视频场景）
      → 到时长后 stop → 报告/指标 → 冷启动 → 落盘证据 JSON。
运行: <venv-python> scripts/executor/run-real-device-acceptance.py --password <pw> --scenario chrome-sports [--duration 600]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import threading
import time
from pathlib import Path

import httpx
import websockets


def adb_cmd(adb: str, device: str, *args: str) -> str:
    out = subprocess.run(
        [adb, "-s", device, *args], capture_output=True, text=True, timeout=60,
    )
    return out.stdout + out.stderr


def _ui_dump(adb: str, device: str, local_path: Path) -> list[dict]:
    """dump 当前 UI 层级并返回节点列表（text/bounds/clickable）。"""
    adb_cmd(adb, device, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
    adb_cmd(adb, device, "pull", "/sdcard/ui.xml", str(local_path))
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(local_path)
        nodes: list[dict] = []
        for node in tree.iter("node"):
            text = node.attrib.get("text", "") or ""
            bounds = node.attrib.get("bounds", "")
            clickable = node.attrib.get("clickable", "false") == "true"
            if text.strip() or clickable:
                nodes.append({
                    "text": text.strip(),
                    "bounds": bounds,
                    "clickable": clickable,
                    "class": node.attrib.get("class", ""),
                })
        return nodes
    except Exception:
        return []


def _bounds_center(bounds: str) -> tuple[int, int] | None:
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def _tap_first(adb: str, device: str, nodes: list[dict], matcher) -> bool:
    for node in nodes:
        if matcher(node) and _bounds_center(node["bounds"]):
            x, y = _bounds_center(node["bounds"])
            adb_cmd(adb, device, "shell", "input", "tap", str(x), str(y))
            print(f"[drive] tapped ({x},{y}) text='{node['text'][:40]}'", flush=True)
            return True
    return False


def drive_scroll(adb: str, device: str, pkg: str, seconds: int) -> None:
    adb_cmd(adb, device, "shell", "am", "force-stop", pkg)
    adb_cmd(adb, device, "shell", "am", "start", "-n", f"{pkg}/.MainActivity")
    time.sleep(5)
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


def drive_chrome_sports(adb: str, device: str, dump_path: Path) -> None:
    """Chrome 打开 www.camel1.tv，任选一场有视频流的比赛（LIVE 卡片）进入。"""
    chrome = "com.android.chrome"
    adb_cmd(adb, device, "shell", "svc", "power", "stayon", "true")
    adb_cmd(adb, device, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb_cmd(adb, device, "shell", "am", "force-stop", chrome)
    adb_cmd(
        adb, device, "shell",
        "am", "start", "-a", "android.intent.action.VIEW",
        "-d", "https://www.camel1.tv",
        "-n", "com.android.chrome/com.google.android.apps.chrome.Main",
    )
    time.sleep(14)
    for attempt in range(3):
        nodes = _ui_dump(adb, device, dump_path)
        # 优先带 LIVE 徽标的赛事卡片；其次首屏赛事条目
        live = [n for n in nodes if n["text"].upper() == "LIVE" or "LIVE" in n["text"].upper()]
        clicked = _tap_first(adb, device, live, lambda n: True)
        if not clicked:
            match_cards = [
                n for n in nodes
                if n["clickable"] and n["bounds"].count("[") >= 2
                and 500 <= _bounds_center(n["bounds"])[1] <= 1600
            ]
            clicked = _tap_first(adb, device, match_cards, lambda n: True)
        if clicked:
            break
        adb_cmd(adb, device, "shell", "input", "swipe", "540", "1600", "540", "700", "400")
        time.sleep(3)
    time.sleep(8)  # 等待视频页加载/起播


def drive_app_live(adb: str, device: str, pkg: str, dump_path: Path) -> None:
    """小象直播 App：启动 → 进入任一直播间（视频流）。"""
    adb_cmd(adb, device, "shell", "svc", "power", "stayon", "true")
    adb_cmd(adb, device, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb_cmd(adb, device, "shell", "am", "force-stop", pkg)
    adb_cmd(adb, device, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(12)
    for attempt in range(3):
        nodes = _ui_dump(adb, device, dump_path)
        room_hits = [
            n for n in nodes
            if any(k in n["text"] for k in ("直播", "Live", "LIVE", "观看", "人"))
            or (n["clickable"] and n["bounds"].count("[") >= 2)
        ]
        clicked = _tap_first(adb, device, room_hits, lambda n: True)
        if clicked:
            break
        adb_cmd(adb, device, "shell", "input", "swipe", "540", "1600", "540", "700", "400")
        time.sleep(3)
    time.sleep(8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default="http://127.0.0.1:8046/api/v1")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", required=True)
    ap.add_argument("--adb", default=r"C:\Users\26029\AppData\Local\Android\Sdk\platform-tools\adb.exe")
    ap.add_argument("--device", default="dcd8891f")
    ap.add_argument("--scenario", choices=["scroll", "chrome-sports", "app-live", "manual"], default="chrome-sports")
    ap.add_argument("--app-pkg", default="")
    ap.add_argument("--duration", type=int, default=600)
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
            "pkg_name": args.app_pkg or "com.android.chrome",
            "metrics": ["cpu", "memory", "fps", "jank", "battery", "network"],
        }).json()["data"]
        sid, ssid = create["id"], create["session_id"]
        print(f"[session] created id={sid} session={ssid} scenario={args.scenario} duration={args.duration}s", flush=True)

        client.post(f"/perf-sessions/{sid}/start", headers=auth).raise_for_status()
        print("[session] started", flush=True)

        ws_headers = {
            "Origin": "http://localhost:5216",
            "Authorization": f"Bearer {token}",
            "X-Project-Id": str(project_id),
        }
        ws_url = base.replace("http://", "ws://") + f"/perf-sessions/{sid}/stream"
        dump_path = Path(args.output_dir) / f"ui-{args.scenario}.xml"
        dump_path.parent.mkdir(parents=True, exist_ok=True)

        samples: list[dict] = []

        if args.scenario == "manual":
            adb_cmd(args.adb, args.device, "shell", "svc", "power", "stayon", "true")
            print("[drive] manual mode — 用户手动驱动目标应用/页面", flush=True)
            drive = threading.Thread(target=lambda: time.sleep(args.duration))
        elif args.scenario == "scroll":
            drive = threading.Thread(
                target=drive_scroll, args=(args.adb, args.device, args.app_pkg or "com.camelrn", max(10, args.duration - 6))
            )
        elif args.scenario == "chrome-sports":
            drive = threading.Thread(target=drive_chrome_sports, args=(args.adb, args.device, dump_path))
        else:
            pkg = args.app_pkg or "com.yiwuzhibo"
            drive = threading.Thread(target=drive_app_live, args=(args.adb, args.device, pkg, dump_path))

        async def run_collection() -> None:
            async with websockets.connect(ws_url, additional_headers=ws_headers) as ws:
                drive.start()
                deadline = time.time() + args.duration
                while time.time() < deadline:
                    try:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except asyncio.TimeoutError:
                        continue
                    samples.append(msg)
                    if msg.get("type") in ("session_end", "error"):
                        break
                try:
                    await ws.send(json.dumps({"action": "stop"}))
                except Exception:
                    pass
                while True:
                    try:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except asyncio.TimeoutError:
                        break
                    samples.append(msg)
                    if msg.get("type") == "session_end":
                        break
                drive.join(timeout=5)

        asyncio.run(run_collection())
        print(f"[stream] messages={len(samples)}", flush=True)

        report = client.get(f"/perf-sessions/{sid}/report", headers=auth).json()["data"]
        for m in report.get("metrics", []):
            print(
                f"[metric] {m['metric_type']} samples={m['samples']} mean={m['mean']} "
                f"min={m['min_val']} max={m['max_val']} passed={m['passed']}",
                flush=True,
            )
        metrics = client.get(f"/perf-sessions/{sid}/metrics", headers=auth).json()["data"]
        print(f"[metrics] total_points={metrics['total_points']}", flush=True)

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        evidence = {
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "scenario": args.scenario,
            "duration_s": args.duration,
            "device": dev,
            "session": create,
            "stream_messages": samples,
            "total_points": metrics["total_points"],
            "report": report,
        }
        evidence_path = out_dir / f"real-device-{args.scenario}.json"
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[evidence] saved: {evidence_path}", flush=True)
        print(f"SESSION={ssid} ID={sid} SCENARIO={args.scenario}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
