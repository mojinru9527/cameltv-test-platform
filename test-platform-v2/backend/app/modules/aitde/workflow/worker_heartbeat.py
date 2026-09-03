"""Continuous Control Plane heartbeat for a managed Durable Runtime Worker."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

OFFLINE_THRESHOLD_SECONDS = 180.0
DEFAULT_HEARTBEAT_SECONDS = 60.0


@dataclass(frozen=True)
class HeartbeatConfig:
    backend_url: str
    api_token: str
    worker_key: str
    name: str
    network_zone: str
    version: str
    machine_identity: str
    capabilities: tuple[str, ...]
    heartbeat_seconds: float

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        hostname: str | None = None,
    ) -> HeartbeatConfig:
        values = os.environ if environ is None else environ
        resolved_hostname = hostname or socket.gethostname()
        worker_key = values.get("WORKER_KEY", f"worker-{resolved_hostname}")
        heartbeat_seconds = float(values.get("WORKER_HEARTBEAT_SECONDS", str(DEFAULT_HEARTBEAT_SECONDS)))
        if not 1 <= heartbeat_seconds < OFFLINE_THRESHOLD_SECONDS:
            raise ValueError("WORKER_HEARTBEAT_SECONDS must be at least 1 and less than 180")

        capabilities = tuple(
            capability.strip().upper()
            for capability in values.get("CAPS", "HTTP,BROWSER").split(",")
            if capability.strip()
        )
        if not capabilities:
            raise ValueError("CAPS must contain at least one capability")

        return cls(
            backend_url=values.get("BACKEND_URL", "http://localhost:8000/api/v2").rstrip("/"),
            api_token=values.get("API_TOKEN", ""),
            worker_key=worker_key,
            name=values.get("WORKER_NAME", worker_key),
            network_zone=values.get("ZONE", "TEST").upper(),
            version=values.get("WORKER_VERSION", "1.0"),
            machine_identity=values.get("MACHINE_IDENTITY", resolved_hostname),
            capabilities=capabilities,
            heartbeat_seconds=heartbeat_seconds,
        )


def build_payload(config: HeartbeatConfig) -> dict[str, object]:
    return {
        "worker_key": config.worker_key,
        "name": config.name,
        "network_zone": config.network_zone,
        "version": config.version,
        "machine_identity": config.machine_identity,
        "tags": {"host": config.machine_identity},
        "capabilities": list(config.capabilities),
    }


async def send_heartbeat(
    client: httpx.AsyncClient,
    config: HeartbeatConfig,
) -> None:
    headers = {}
    if config.api_token:
        headers["Authorization"] = f"Bearer {config.api_token}"
    response = await client.post(
        f"{config.backend_url}/workers/heartbeat",
        json=build_payload(config),
        headers=headers,
    )
    response.raise_for_status()
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError("Worker heartbeat returned invalid JSON") from exc
    if not isinstance(body, dict) or body.get("code") != 0:
        message = body.get("message", "unknown error") if isinstance(body, dict) else "invalid response"
        raise RuntimeError(f"Worker heartbeat rejected: {message}")


async def _wait_for_next_heartbeat(
    stop_event: asyncio.Event,
    seconds: float,
) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def _run_loop(
    config: HeartbeatConfig,
    stop_event: asyncio.Event,
    send: Callable[[HeartbeatConfig], Awaitable[None]],
    wait: Callable[[asyncio.Event, float], Awaitable[None]],
) -> None:
    while not stop_event.is_set():
        try:
            await send(config)
            logger.info("[worker] heartbeat sent key=%s", config.worker_key)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - a transient control-plane failure must retry
            logger.warning("[worker] heartbeat failed; retrying: %s", exc)
        await wait(stop_event, config.heartbeat_seconds)


async def run_heartbeat_loop(
    config: HeartbeatConfig,
    stop_event: asyncio.Event,
    *,
    send: Callable[[HeartbeatConfig], Awaitable[None]] | None = None,
    wait: Callable[[asyncio.Event, float], Awaitable[None]] = _wait_for_next_heartbeat,
) -> None:
    if send is not None:
        await _run_loop(config, stop_event, send, wait)
        return

    async with httpx.AsyncClient(timeout=10.0) as client:

        async def send_with_client(current: HeartbeatConfig) -> None:
            await send_heartbeat(client, current)

        await _run_loop(config, stop_event, send_with_client, wait)


async def _run_from_environment() -> None:
    config = HeartbeatConfig.from_environment()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop_event.set)
        except NotImplementedError:
            pass
    await run_heartbeat_loop(config, stop_event)


def main() -> int:
    try:
        asyncio.run(_run_from_environment())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
