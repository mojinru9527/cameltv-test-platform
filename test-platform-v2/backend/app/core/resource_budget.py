"""Same-host heavy-task leases backed by kernel locks on a shared local volume.

Business task ownership remains in task_queue. JSON is bounded diagnostic
state, never the source of lock ownership; crash recovery needs no stale TTL.
"""
from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Callable
import uuid

from filelock import FileLock, SoftFileLock, Timeout

logger = logging.getLogger(__name__)
MemorySampler = Callable[[], tuple[str, int | None]]


class BudgetCancelled(RuntimeError):
    """Waiting task was cancelled before receiving capacity."""


class BudgetTimeout(TimeoutError):
    """Capacity was not available within the caller's admission deadline."""


def sample_memory() -> tuple[str, int | None]:
    for filename in ('/sys/fs/cgroup/memory.current',
                     '/sys/fs/cgroup/memory/memory.usage_in_bytes'):
        try:
            return 'container', int(Path(filename).read_text().strip())
        except (OSError, ValueError):
            continue
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return 'process', int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        logger.debug('Process RSS is unavailable on this host')
    return 'unknown', None


def _write_json(path: Path, value: dict) -> None:
    # Fixed temporary names bound disk growth even if a holder crashes mid-write.
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')
    temporary.replace(path)


def _kernel_lock(path: Path) -> FileLock:
    lock = FileLock(path, thread_local=False)
    if isinstance(lock, SoftFileLock):
        raise RuntimeError('heavy-task budget requires kernel-backed file locks')
    return lock


class ResourceLease:
    def __init__(self, lock: FileLock, status_path: Path, kind: str,
                 task_id: str, sampler: MemorySampler) -> None:
        self._lock = lock
        self._path = status_path
        self._sampler = sampler
        self._stop = threading.Event()
        self._release_guard = threading.Lock()
        self._released = False
        self._started = time.monotonic()
        self._state = {
            'lease_id': uuid.uuid4().hex, 'kind': kind, 'task_id': task_id,
            'pid': os.getpid(), 'state': 'running', 'started_at': time.time(),
            'memory_scope': 'unknown', 'observed_peak_bytes': None,
        }
        self._sample()
        _write_json(self._path, self._state)
        self._thread = threading.Thread(target=self._observe, daemon=True,
                                        name='heavy-task-memory')
        self._thread.start()

    def _sample(self) -> None:
        try:
            scope, value = self._sampler()
            if value is not None:
                if self._state['memory_scope'] != scope:
                    self._state['observed_peak_bytes'] = value
                else:
                    self._state['observed_peak_bytes'] = max(
                        self._state['observed_peak_bytes'] or 0, value,
                    )
                self._state['memory_scope'] = scope
        except (OSError, ValueError):
            logger.warning('Heavy-task memory observation failed', exc_info=True)

    def _observe(self) -> None:
        while not self._stop.wait(2):
            self._sample()

    def bind_task(self, task_id: str) -> None:
        if not re.fullmatch(r'[A-Za-z0-9:_.-]{1,100}', str(task_id)):
            raise ValueError('task identity must be an opaque ID')
        with self._release_guard:
            if self._released:
                raise RuntimeError('cannot bind a released lease')
            self._state['task_id'] = str(task_id)
            _write_json(self._path, self._state)

    def release(self, outcome: str = 'finished') -> None:
        with self._release_guard:
            if self._released:
                return
            self._stop.set()
            self._thread.join(timeout=3)
            try:
                self._sample()
                self._state.update(state='released', outcome=outcome,
                                   elapsed_seconds=round(time.monotonic() - self._started, 3))
                _write_json(self._path, self._state)
                logger.info('Heavy-task resource released: %s', json.dumps(self._state))
            except OSError:
                logger.warning('Could not persist resource telemetry', exc_info=True)
            finally:
                self._lock.release()
                self._released = True

    def __enter__(self) -> ResourceLease:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release('error' if exc_type else 'finished')


class FileBudget:
    def __init__(self, directory: Path, capacity: int,
                 sampler: MemorySampler = sample_memory) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or not 1 <= capacity <= 32:
            raise ValueError('capacity must be an integer from 1 to 32')
        self.directory = directory.resolve()
        self.capacity = capacity
        self.sampler = sampler

    def _validate_policy(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        with _kernel_lock(self.directory / 'policy.lock').acquire(timeout=5):
            policy_path = self.directory / 'policy.json'
            expected = {'version': 1, 'capacity': self.capacity}
            if policy_path.exists():
                if json.loads(policy_path.read_text(encoding='utf-8')) != expected:
                    raise ValueError('shared capacity policy differs; quiesce workers before changing it')
            else:
                _write_json(policy_path, expected)

    def try_acquire(self, kind: str, task_id: str) -> ResourceLease | None:
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', kind):
            raise ValueError('invalid workload kind')
        if not re.fullmatch(r'[A-Za-z0-9:_.-]{1,100}', str(task_id)):
            raise ValueError('task identity must be an opaque ID, not task contents')
        self._validate_policy()
        for slot in range(self.capacity):
            lock = _kernel_lock(self.directory / f'slot-{slot}.lock')
            try:
                lock.acquire(timeout=0)
            except Timeout:
                continue
            try:
                return ResourceLease(lock, self.directory / f'slot-{slot}.json',
                                     kind, str(task_id), self.sampler)
            except BaseException:
                lock.release()
                raise
        return None

    def wait(self, kind: str, task_id: str, *, timeout: float,
             cancelled: Callable[[], bool] | None = None,
             poll_interval: float = 0.1) -> ResourceLease:
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError('admission timeout must be finite and nonnegative')
        if not math.isfinite(poll_interval) or poll_interval <= 0:
            raise ValueError('poll interval must be finite and positive')
        deadline = time.monotonic() + timeout
        while True:
            if cancelled and cancelled():
                raise BudgetCancelled('task cancelled while waiting for capacity')
            lease = self.try_acquire(kind, task_id)
            if lease is not None:
                try:
                    if cancelled and cancelled():
                        raise BudgetCancelled('task cancelled before execution')
                except BaseException:
                    lease.release('cancelled')
                    raise
                return lease
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BudgetTimeout('heavy-task capacity unavailable')
            time.sleep(min(poll_interval, remaining))


def configured_budget(resource_class: str = 'execution') -> FileBudget | None:
    from app.core.config import settings

    if resource_class not in ('execution', 'orchestration'):
        raise ValueError('unknown resource class')
    if not settings.heavy_task_budget_enabled:
        return None
    directory = settings.heavy_task_budget_dir or str(
        Path(__file__).resolve().parents[2] / 'storage' / 'resource-budget',
    )
    if resource_class == 'orchestration':
        return FileBudget(Path(directory) / 'orchestration', settings.orchestration_budget_capacity)
    return FileBudget(Path(directory), settings.heavy_task_budget_capacity)
