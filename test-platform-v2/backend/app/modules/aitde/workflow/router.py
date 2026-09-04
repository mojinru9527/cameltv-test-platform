"""AITDE V3.4 TaskQueueRouter (V34-006).

Selects a Temporal TaskQueue from ``(network_zone, required_capabilities, tags)``.
The LLM never chooses a machine — the router only ever chooses a Queue; a worker
pulls from that queue by its registered capabilities.

Refuses a routing request whose required capabilities are not served by any
ONLINE worker in the zone (e.g. ``BROWSER`` must never go to an HTTP-only queue).
"""
from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import NetworkZone, WorkerStatus
from app.modules.aitde.workflow import repository

# Plan §1 queues. PROD_RO is V3.6 scope; only registered here as reserved.
_ZONE_QUEUE: dict[str, str] = {
    NetworkZone.OFFICE.value: "worker-office",
    NetworkZone.TEST.value: "worker-test",
    NetworkZone.PROD_RO.value: "worker-prod-ro",
}


class TaskQueueRouter:
    """Route a run to a queue by zone + capabilities (V34-006)."""

    def select_queue(
        self,
        db: Session,
        *,
        network_zone: str,
        required_capabilities: Sequence[str],
        tags: dict | None = None,
    ) -> str:
        zone_queue = _ZONE_QUEUE.get(network_zone)
        if zone_queue is None:
            raise APIException(
                code=400, msg=f"未知网络分区：{network_zone}", http_status=422
            )

        repository.mark_offline_workers(db)
        workers = repository.list_workers(db)
        for w in workers:
            if w.network_zone != network_zone:
                continue
            if w.status != WorkerStatus.ONLINE.value:
                continue
            caps = {c.capability for c in repository.list_worker_capabilities(db, w.id)}
            if set(required_capabilities) <= caps:
                return zone_queue

        # No ONLINE worker in the zone serves the full capability set.
        raise APIException(
            code=400,
            msg=(
                f"无匹配 Worker/Queue：zone={network_zone} "
                f"capabilities={sorted(required_capabilities)}"
            ),
            http_status=422,
        )


task_queue_router = TaskQueueRouter()
