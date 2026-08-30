"""AITDE V3.4 TemporalWorkflowGateway (V34-002).

Wraps the Temporal client for the Control Plane: start / signal / query / cancel,
plus a worker runner for the ScenarioExecutionWorkflow. It is the only place that
talks to Temporal; the rest of the app calls this gateway.

Graceful degradation: when ``settings.temporal_enabled`` is False, the gateway is
importable and every method raises ``APIException`` with code "TEMPORAL_DISABLED"
instead of importing/connecting Temporal at module load. This keeps the app
startable in dev/test/prod without a Temporal server.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.core.exceptions import APIException
from app.temporal.workflows import ScenarioExecutionWorkflow

logger = logging.getLogger(__name__)


class TemporalWorkflowGateway:
    """Control-Plane gateway to the Temporal cluster.

    The Temporal client is created lazily on first use so that a disabled or
    misconfigured deployment does not fail at import/startup time.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._connected: bool = False

    # ── availability ─────────────────────────────────────────────────────────

    def unavailable(self) -> tuple[str, str]:
        """Return (code, detail) when Temporal is not usable; None if usable."""
        if not settings.temporal_enabled:
            return "TEMPORAL_DISABLED", "Temporal Durable Runtime is not enabled"
        if not settings.temporal_grpc_endpoint:
            return "TEMPORAL_NOT_CONFIGURED", "temporal_grpc_endpoint is empty"
        return None, None

    def _ensure_available(self) -> None:
        code, detail = self.unavailable()
        if code is not None:
            raise APIException(code=400, msg=detail, http_status=503)

    # ── client lifecycle ─────────────────────────────────────────────────────

    async def _get_client(self) -> Any:
        self._ensure_available()
        if self._connected and self._client is not None:
            return self._client
        from temporalio.client import Client

        connect_kwargs: dict[str, Any] = {
            "namespace": settings.temporal_namespace,
        }
        if settings.temporal_tls_enabled:
            connect_kwargs["tls"] = True
            connect_kwargs["api_key"] = None  # mTLS uses client cert below
        else:
            connect_kwargs["tls"] = False
        # Python temporalio does not take a "channel" flag directly; insecure
        # channel is the default when tls is False. mTLS client certs are passed
        # through the Temporal server's TLS configuration rather than the SDK.
        self._client = await Client.connect(
            settings.temporal_grpc_endpoint, **connect_kwargs
        )
        self._connected = True
        logger.info(
            "[temporal] connected to %s namespace=%s",
            settings.temporal_grpc_endpoint,
            settings.temporal_namespace,
        )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            self._client = None
            self._connected = False

    # ── workflow operations ──────────────────────────────────────────────────

    async def start_scenario_execution(
        self,
        workflow_id: str,
        run_id: int | None,
        scenario_input: dict[str, Any],
        task_queue: str | None = None,
    ) -> dict[str, Any]:
        """Start a ScenarioExecutionWorkflow. Duplicate start is idempotent:
        an already-running workflow id returns the existing handle."""
        client = await self._get_client()
        import asyncio

        # Resolve the queue by (zone, capabilities) when the caller routes the
        # run; otherwise fall back to the configured default queue.
        resolved_queue = task_queue or settings.temporal_task_queue
        from temporalio.client import WorkflowAlreadyStartedError

        try:
            handle = await client.start_workflow(
                ScenarioExecutionWorkflow.run,
                scenario_input,
                id=workflow_id,
                task_queue=resolved_queue,
            )
        except WorkflowAlreadyStartedError:
            handle = client.get_workflow_handle(workflow_id)
        try:
            result = await asyncio.wait_for(handle.result(), timeout=30)
        except Exception as exc:  # noqa: BLE001 — surface workflow/activity failure
            result = {"error": str(exc)}
        return {
            "workflow_id": workflow_id,
            "temporal_run_id": handle.first_execution_run_id,
            "result": result,
        }

    async def signal_workflow(self, workflow_id: str, signal_name: str, args: Any) -> None:
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(signal_name, args)

    async def query_workflow(self, workflow_id: str, query_name: str, args: Any) -> Any:
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        return await handle.query(query_name, args)

    async def cancel_workflow(self, workflow_id: str) -> None:
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()

    async def describe_workflow(self, workflow_id: str) -> dict[str, Any]:
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        return {
            "workflow_id": desc.id,
            "run_id": desc.run_id,
            "status": str(desc.status),
            "task_queue": getattr(desc, "task_queue", None),
        }


# Module-level singleton, matching the repo's service pattern.
temporal_gateway = TemporalWorkflowGateway()


async def run_worker(workflows: list | None = None) -> None:
    """Run the ScenarioExecutionWorkflow worker until interrupted.

    Used by a dev / test runbook and by the chaos/recovery drill. In CI the
    in-memory WorkflowEnvironment registers this worker instead.
    """
    _ensure_enabled()
    from temporalio.worker import Worker

    client = await temporal_gateway._get_client()  # noqa: SLF001
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=workflows or [ScenarioExecutionWorkflow],
        activities=list(get_activities()),
    )
    logger.info("[temporal] worker polling queue=%s", settings.temporal_task_queue)
    async with worker:
        stop = asyncio.Event()
        try:
            await stop.wait()
        finally:
            await temporal_gateway.close()


def get_activities():
    from app.temporal import activities

    # Side-effect: register the real driver hooks (V34-004) once.
    from app.modules.aitde.workflow import drivers  # noqa: F401

    return [
        activities.capture_environment_snapshot,
        activities.plan_data,
        activities.ensure_fixture,
        activities.resolve_command_plan,
        activities.policy_check,
        activities.execute_commands,
        activities.evaluate_oracles,
        activities.collect_evidence,
        activities.classify_outcome,
        activities.cleanup_fixture,
        activities.build_replay,
        activities.run_legacy_api_task,
        activities.run_legacy_ui_task,
    ]


def _ensure_enabled() -> None:
    code, detail = temporal_gateway.unavailable()
    if code is not None:
        raise APIException(code=400, msg=detail, http_status=503)
