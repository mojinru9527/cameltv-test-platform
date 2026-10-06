"""Verify the RENDERED compose topology (after extends/merge) holds the P0-4 invariants.

Runs `docker compose config --format json` for both the split default and the
combined rollback overlay, then asserts which services actually receive the
plaintext cloud credentials. This is stronger than asserting on the raw YAML:
it proves the merge/extends result, which is what Docker actually deploys.
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
AI_GATEWAY_TOKEN=probe-token
AI_GATEWAY_IMAGE=cameltv-tp-ai-gateway:probe
API_IMAGE=cameltv-tp-api:probe
API_MEMORY_LIMIT=512m
RUNNER_IMAGE=cameltv-tp-runner:probe
RUNNER_MEMORY_LIMIT=512m
AI_GATEWAY_MEMORY_LIMIT=512m
TEMPORAL_WORKER_MEMORY_LIMIT=512m
AI_API_KEY=sk-PROBEVALUE
DSH_API_KEY=sk-PROBEDSH
"""


def render(files: list[str], env_file: Path, profiles: tuple[str, ...] = ()) -> dict:
    # `aitde-worker` 声明了 `profiles: ["aitde-worker"]`，不加 --profile 时
    # `docker compose config` 会把它整个排除掉——那样「该服务是否拿到 DSH Key」
    # 就永远不会被检查到，属于典型的静默漏检。
    out = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file),
         *[a for p in profiles for a in ("--profile", p)],
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

    split = render(["docker-compose.yml", "docker-compose.execution.yml"], env_file, ("aitde-worker",))
    print("== split default topology (docker-compose.yml + execution.yml) ==")
    if not check("AI_API_KEY", holders(split, "AI_API_KEY"), {"ai-gateway"}):
        failures += 1
    if not check("DSH_API_KEY", holders(split, "DSH_API_KEY"), {"runner", "aitde-worker"}):
        failures += 1

    base_only = render(["docker-compose.yml"], env_file, ("aitde-worker",))
    print("\n== base file only (aitde-worker profile path) ==")
    if not check("AI_API_KEY", holders(base_only, "AI_API_KEY"), {"ai-gateway"}):
        failures += 1
    if not check("DSH_API_KEY", holders(base_only, "DSH_API_KEY"), {"runner", "aitde-worker"}):
        failures += 1

    print("\n== rolled-back combined topology (docker-compose.yml + combined.yml) ==")
    # 回滚到合并镜像后 backend 在进程内做 AI + DSH，因此两把 Key 都必须回到 backend；
    # 同时 aitde-worker 仍是独立执行服务（WORKER_EXECUTION_ENABLED=true，会派生 DSH
    # 子进程），所以它保留 DSH Key 是**正确设计**而非泄漏，期望集合必须含它。
    combined = render(["docker-compose.yml", "docker-compose.combined.yml"], env_file, ("aitde-worker",))
    if not check("AI_API_KEY", holders(combined, "AI_API_KEY"), {"backend"}):
        failures += 1
    if not check("DSH_API_KEY", holders(combined, "DSH_API_KEY"), {"backend", "aitde-worker"}):
        failures += 1

    print("\n== published host bindings ==")
    for label, model in (("split", split), ("combined", combined)):
        for name, svc in (model.get("services") or {}).items():
            for port in svc.get("ports") or []:
                host_ip = port.get("host_ip")
                pub = port.get("published")
                target = port.get("target")
                flag = "OK  " if host_ip in ("127.0.0.1", "") else "FAIL"
                if host_ip not in ("127.0.0.1", ""):
                    failures += 1
                print(f"{flag} {label}/{name}: host_ip={host_ip!r} published={pub} -> target={target}")

print()
if failures:
    print(f"{failures} CHECK(S) FAILED")
    sys.exit(1)
print("ALL RENDERED-TOPOLOGY CHECKS PASSED")
