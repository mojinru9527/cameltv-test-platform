"""Mock Server：容器化 WireMock 编排。

- up/down     启停 WireMock 容器（docker compose），加载站点 stub
- convert     把 traffic_monitor 录制转换为 WireMock stub 映射
- inject      经 WireMock Admin API 注入故障（500 / 超时 / 空响应）

依赖：Docker Desktop。被测系统把下游 base_url 指向 http://localhost:<port> 即可。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import httpx

from core import logging as log
from core.recording import load_entries

ROOT = Path(__file__).resolve().parent.parent.parent
WIREMOCK_DIR = ROOT / "docker" / "wiremock"
COMPOSE = WIREMOCK_DIR / "docker-compose.yml"


def _mappings_dir(site: str) -> Path:
    d = WIREMOCK_DIR / "mappings" / site
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# 容器启停
# --------------------------------------------------------------------------- #
def up(site: str, port: int = 8080) -> None:
    mappings = _mappings_dir(site)
    files = WIREMOCK_DIR / "__files"
    files.mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ,
        MOCK_MAPPINGS=str(mappings),
        MOCK_FILES=str(files),
        MOCK_PORT=str(port),
    )
    log.rule(f"Mock Server · {site}")
    log.info(f"stub 目录：{mappings}")
    rc = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "up", "-d"],
        env=env, check=False,
    ).returncode
    if rc != 0:
        log.err("启动失败。请确认 Docker Desktop 已运行。")
        raise SystemExit(1)
    log.ok(f"WireMock 已启动：http://localhost:{port}")
    log.info(f"Admin：http://localhost:{port}/__admin/mappings")
    log.info(f"把被测系统下游 base_url 指向 http://localhost:{port} 即可。")


def down() -> None:
    subprocess.run(["docker", "compose", "-f", str(COMPOSE), "down"], check=False)
    log.ok("WireMock 已停止。")


# --------------------------------------------------------------------------- #
# 录制 → stub
# --------------------------------------------------------------------------- #
def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:40]


def convert(site: str, recording: str) -> None:
    entries = load_entries(recording)
    out_dir = _mappings_dir(site)
    count = 0
    for i, e in enumerate(entries):
        req, resp = e["request"], e["response"]
        mapping = {
            "request": {
                "method": req["method"],
                "urlPath": req["path"],
            },
            "response": {
                "status": resp["status"],
                "headers": {"Content-Type": "application/json"},
            },
        }
        # 带查询参数精确匹配（提高命中准确度）
        if req.get("query"):
            mapping["request"]["queryParameters"] = {
                k: {"equalTo": str(v)} for k, v in req["query"].items()
            }
        body = resp.get("body", "")
        if isinstance(body, (dict, list)):
            mapping["response"]["jsonBody"] = body
        else:
            mapping["response"]["body"] = str(body)

        fname = f"{i:03d}-{req['method']}-{_slug(req['path'])}.json"
        (out_dir / fname).write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        count += 1
    log.ok(f"已生成 {count} 条 stub → {out_dir}")
    log.info("重启或热加载：tp mock up 后 WireMock 自动读取 mappings/。")


# --------------------------------------------------------------------------- #
# 故障注入（Admin API）
# --------------------------------------------------------------------------- #
def inject(path: str, status: int = 500, scenario: str = "", port: int = 8080) -> None:
    admin = f"http://localhost:{port}/__admin/mappings"
    response: dict = {"status": status}
    if scenario == "timeout":
        response = {"status": 200, "fixedDelayMilliseconds": 60000}
    elif scenario == "empty":
        response = {"fault": "EMPTY_RESPONSE"}
    elif scenario == "malformed":
        response = {"fault": "MALFORMED_RESPONSE_CHUNK"}
    else:
        response["jsonBody"] = {"error": "injected fault", "status": status}

    stub = {
        "priority": 1,  # 高优先级覆盖已有 stub
        "request": {"method": "ANY", "urlPath": path},
        "response": response,
    }
    try:
        r = httpx.post(admin, json=stub, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        log.err(f"注入失败（WireMock 未启动？）：{exc}")
        raise SystemExit(1)
    desc = scenario or f"status={status}"
    log.ok(f"已对 {path} 注入故障：{desc}")
    log.info("移除注入：tp mock down 后重新 up，或调用 DELETE /__admin/mappings。")
