"""V16-024/P1-9：镜像运行态冒烟（生产配置 + 迁移单头 + /health）。

只在本机启动容器，使用一次性随机密钥（不打印、不落盘），结束后删除容器。
产出 `docs/aiqe/v1.6/evidence/image-runtime-smoke.json`，不包含任何密钥值。

用法
----
    python scripts/aiqe/verify_image_runtime.py --image cameltv-aiqe-api:<sha>
"""
from __future__ import annotations

import argparse
import json
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/evidence/image-runtime-smoke.json"
CONTAINER = "aiqe-v16-image-smoke"


def _single_head(output: str) -> str:
    heads = [line.strip() for line in output.splitlines() if line.strip().endswith("(head)")]
    return heads[0] if len(heads) == 1 else ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run(command: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )


def _wait_health(port: int, timeout_seconds: int = 240) -> tuple[int, str]:
    deadline = time.time() + timeout_seconds
    last = (0, "")
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
                return response.status, response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last = (exc.code, "")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(3)
    return last


def verify(image: str, output: Path) -> dict:
    inspect = _run(["docker", "image", "inspect", "--format", "{{.Id}}", image])
    if inspect.returncode != 0:
        raise RuntimeError(f"镜像不存在: {inspect.stderr[:300]}")
    image_id = inspect.stdout.strip()
    port = _free_port()
    _run(["docker", "rm", "-f", CONTAINER])
    start = _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER,
            "-e",
            f"SECRET_KEY={secrets.token_urlsafe(48)}",
            "-e",
            f"ADMIN_PASSWORD=Smoke-{secrets.token_urlsafe(18)}",
            "-e",
            f"TESTER_PASSWORD=Smoke-{secrets.token_urlsafe(18)}",
            "-e",
            f"AI_API_KEY=sk-{secrets.token_urlsafe(24)}",
            "-e",
            "COOKIE_SECURE=true",
            "-e",
            "ENVIRONMENT=production",
            "-e",
            "DATABASE_URL=sqlite:////app/storage/smoke.db",
            "-p",
            f"{port}:8000",
            image,
        ]
    )
    if start.returncode != 0:
        raise RuntimeError(f"容器启动失败: {start.stderr[:300]}")
    try:
        health_status, health_body = _wait_health(port)
        heads = _run(["docker", "exec", CONTAINER, "alembic", "heads"])
        head = _single_head(heads.stdout)
        report = {
            "schema_version": "1.0",
            "artifact_kind": "image-runtime-smoke",
            "generated_at": datetime.now(UTC).isoformat(),
            "image": image,
            "image_id": image_id,
            "container": CONTAINER,
            "environment": "production",
            "health_status": health_status,
            "health_body": health_body[:200],
            "alembic_head": head,
            "migration_single_head": bool(head),
            "status": "PASS" if health_status == 200 and head else "FAIL",
            "note": "一次性随机密钥，未记录任何密钥值；容器已删除。",
        }
        return report
    finally:
        _run(["docker", "rm", "-f", CONTAINER])


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="镜像运行态冒烟")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    try:
        report = verify(args.image, Path(args.output))
    except Exception as exc:  # noqa: BLE001
        print(f"::error::[image-runtime] {type(exc).__name__}: {exc}")
        return 1
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {"status": report["status"], "health": report["health_status"], "head": report["alembic_head"]},
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
