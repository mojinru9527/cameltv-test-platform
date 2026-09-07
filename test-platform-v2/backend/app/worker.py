"""Persistent task consumers, separate from the HTTP application process."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import logging
from pathlib import Path
import signal
import threading
import time

from app.core.config import settings

logger = logging.getLogger(__name__)
HEARTBEAT_PATH = Path('/tmp/platform-worker.heartbeat')


@contextmanager
def task_consumers():
    if not settings.worker_execution_enabled:
        raise RuntimeError('worker process requires WORKER_EXECUTION_ENABLED=true')
    import app.models  # noqa: F401
    from app.core.scheduler import init_scheduler, shutdown_scheduler, scheduler
    from app.services import ai_tasks, api_task_worker
    from app.services.dsh import dsh_task_service
    from app.services.knowledge import agent_queue
    from app.services.ui_runner_queue import shutdown_processor

    with ExitStack() as cleanup:
        cleanup.callback(lambda: shutdown_scheduler() if scheduler.running else None)
        init_scheduler()
        cleanup.callback(shutdown_processor)
        for start, shutdown in (
            (ai_tasks.ensure_worker_running, ai_tasks.shutdown_worker),
            (api_task_worker.ensure_processor_running, api_task_worker.shutdown_processor),
            (dsh_task_service.ensure_worker_running, dsh_task_service.shutdown_worker),
            (agent_queue.ensure_processor_running, agent_queue.shutdown_processor),
        ):
            cleanup.callback(shutdown)
            start()
        # Stop admission before draining consumers; the earlier callback also
        # covers a startup failure before all consumers have been registered.
        cleanup.callback(lambda: shutdown_scheduler() if scheduler.running else None)

        def healthy():
            return (scheduler.running and ai_tasks._loop.is_running()
                    and api_task_worker._loop.is_running()
                    and dsh_task_service._loop.is_running()
                    and agent_queue.processor_is_running())

        yield healthy


def run_worker(stop: threading.Event, heartbeat_path: Path = HEARTBEAT_PATH) -> None:
    heartbeat_path.unlink(missing_ok=True)
    with ExitStack() as cleanup:
        cleanup.callback(heartbeat_path.unlink, missing_ok=True)
        healthy = cleanup.enter_context(task_consumers())
        cleanup.callback(heartbeat_path.unlink, missing_ok=True)
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        while not stop.is_set():
            if not healthy():
                raise RuntimeError('A required task consumer stopped')
            heartbeat_path.write_text(str(time.time()), encoding='ascii')
            stop.wait(5)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    run_worker(stop)


if __name__ == '__main__':
    main()
