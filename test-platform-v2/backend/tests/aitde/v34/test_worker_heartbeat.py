"""Managed Runtime Worker heartbeat lifecycle tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from app.modules.aitde.workflow.worker_heartbeat import (
    HeartbeatConfig,
    build_payload,
    run_heartbeat_loop,
    send_heartbeat,
)


def _config(**overrides) -> HeartbeatConfig:
    defaults = {
        "backend_url": "https://control.example/api/v2",
        "api_token": "worker-token",
        "worker_key": "worker-prod-a",
        "name": "生产只读执行节点 A",
        "network_zone": "PROD_RO",
        "version": "1.0",
        "machine_identity": "prod-node-a",
        "capabilities": ("HTTP", "BROWSER"),
        "heartbeat_seconds": 60.0,
    }
    defaults.update(overrides)
    return HeartbeatConfig(**defaults)


def test_environment_config_defaults_below_offline_threshold():
    config = HeartbeatConfig.from_environment(
        {
            "BACKEND_URL": "https://control.example/api/v2/",
            "WORKER_KEY": "worker-prod-a",
            "ZONE": "PROD_RO",
            "CAPS": "HTTP,BROWSER",
        },
        hostname="prod-node-a",
    )

    assert config.backend_url == "https://control.example/api/v2"
    assert config.heartbeat_seconds == 60.0
    assert config.name == "worker-prod-a"
    assert config.machine_identity == "prod-node-a"
    assert config.capabilities == ("HTTP", "BROWSER")

    with pytest.raises(ValueError, match="less than 180"):
        HeartbeatConfig.from_environment(
            {"WORKER_HEARTBEAT_SECONDS": "180"},
            hostname="prod-node-a",
        )


def test_build_payload_contains_stable_worker_identity():
    assert build_payload(_config()) == {
        "worker_key": "worker-prod-a",
        "name": "生产只读执行节点 A",
        "network_zone": "PROD_RO",
        "version": "1.0",
        "machine_identity": "prod-node-a",
        "tags": {"host": "prod-node-a"},
        "capabilities": ["HTTP", "BROWSER"],
    }


@pytest.mark.anyio
async def test_send_heartbeat_posts_bearer_token_and_validates_envelope():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 0, "message": "success", "data": {}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await send_heartbeat(client, _config())

    assert len(requests) == 1
    assert requests[0].url == "https://control.example/api/v2/workers/heartbeat"
    assert requests[0].headers["authorization"] == "Bearer worker-token"


@pytest.mark.anyio
async def test_heartbeat_loop_retries_transient_failure_and_stops_cleanly():
    stop_event = asyncio.Event()
    attempts = 0
    waits: list[float] = []

    async def fake_send(_config: HeartbeatConfig) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("control plane unavailable")

    async def fake_wait(event: asyncio.Event, seconds: float) -> None:
        waits.append(seconds)
        if attempts >= 2:
            event.set()

    await run_heartbeat_loop(
        _config(),
        stop_event,
        send=fake_send,
        wait=fake_wait,
    )

    assert attempts == 2
    assert waits == [60.0, 60.0]


@pytest.mark.anyio
async def test_heartbeat_loop_does_not_send_after_stop():
    stop_event = asyncio.Event()
    stop_event.set()
    called = False

    async def fake_send(_config: HeartbeatConfig) -> None:
        nonlocal called
        called = True

    await run_heartbeat_loop(_config(), stop_event, send=fake_send)

    assert called is False


def test_worker_launcher_manages_heartbeat_and_gateway_processes():
    platform_root = Path(__file__).resolve().parents[4]
    script = (platform_root / "deploy" / "aitde-runtime" / "scripts" / "start-worker.sh").read_text(encoding="utf-8")

    assert 'cd "$(dirname "$0")/../../../backend"' in script
    assert "app.modules.aitde.workflow.worker_heartbeat" in script
    assert "app.modules.aitde.workflow.gateway" in script
    assert "wait -n" in script
    assert "trap" in script
    assert "curl -sS -X POST" not in script
