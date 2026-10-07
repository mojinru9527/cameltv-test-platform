"""Verify the RENDERED compose topology (after extends/merge) holds the credential invariants.

平台简化批次：ai-gateway 独立服务与 aitde-worker 已删除，部署面只剩
`docker-compose.yml`（api + runner + postgres + frontend）。本脚本用
`docker compose config --format json` 证明**合并/extends 之后**的凭据归属，
比断原始 YAML 更强——它检查的是 Docker 真正部署的结果。

固化不变式：
1. `AI_API_KEY` 只在 `backend`（平台直连 AI；runner 不得持有云端明文 Key）。
2. 已退役的 `DSH_API_KEY` 不得出现在任何服务。
3. 所有发布到宿主机的端口只绑定回环（入站流量必须经反向代理）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEPLOY = Path(sys.argv[1]).resolve()

BASE_ENV = """ENVIRONMENT=production
POSTGRES_PASSWORD=probe
SECRET_KEY=probe-secret
ADMIN_PASSWORD=probe-admin
TESTER_PASSWORD=probe-tester
COOKIE_SECURE=true
DATABASE_URL=postgresql://cameltv:probe@postgres:5432/probe
API_IMAGE=cameltv-tp-api:probe
API_MEMORY_LIMIT=512m
RUNNER_IMAGE=cameltv-tp-runner:probe
RUNNER_MEMORY_LIMIT=512m
AI_API_KEY=sk-PROBEVALUE
DSH_API_KEY=sk-PROBEDSH
"""


def render(files: list[str], env_file: Path) -> dict:
    out = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file),
         *[a for f in files for a in ("-f", str(DEPLOY / f))],
         "config", "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def holders(model: dict, key: str) -> set[str]:
    found = set()
    for name, svc in (model.get("services") or {}).items():
        env = svc.get("environment") or {}
        if env.get(key) not in (None, ""):
            found.add(name)
    return found


def check(label: str, got: set[str], expected: set[str]) -> bool:
    ok = got == expected
    print(f"{'OK  ' if ok else 'FAIL'} {label}: holders={sorted(got)} expected={sorted(expected)}")
    return ok


failures = 0
with tempfile.TemporaryDirectory() as td:
    env_file = Path(td) / "probe.env"
    env_file.write_text(BASE_ENV, encoding="utf-8")

    model = render(["docker-compose.yml"], env_file)
    print("== simplified default topology (docker-compose.yml) ==")
    if not check("AI_API_KEY", holders(model, "AI_API_KEY"), {"backend"}):
        failures += 1
    if not check("DSH_API_KEY (retired)", holders(model, "DSH_API_KEY"), set()):
        failures += 1
    for gone in ("ai-gateway", "aitde-worker"):
        if gone in (model.get("services") or {}):
            print(f"FAIL retired service still rendered: {gone}")
            failures += 1
        else:
            print(f"OK   retired service absent: {gone}")

    print("\n== published host bindings ==")
    for name, svc in (model.get("services") or {}).items():
        for port in svc.get("ports") or []:
            host_ip = port.get("host_ip")
            pub = port.get("published")
            target = port.get("target")
            flag = "OK  " if host_ip in ("127.0.0.1", "") else "FAIL"
            if host_ip not in ("127.0.0.1", ""):
                failures += 1
            print(f"{flag} {name}: host_ip={host_ip!r} published={pub} -> target={target}")

print()
if failures:
    print(f"{failures} CHECK(S) FAILED")
    sys.exit(1)
print("ALL RENDERED-TOPOLOGY CHECKS PASSED")
