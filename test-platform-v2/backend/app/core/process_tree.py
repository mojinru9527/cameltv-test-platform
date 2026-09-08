"""Owned process groups for the single-host Linux production runner."""
from __future__ import annotations

import os
import logging
import signal
import subprocess

logger = logging.getLogger(__name__)


def process_group_options() -> dict:
    return {'start_new_session': True} if os.name == 'posix' else {}


def terminate_process_tree(proc: subprocess.Popen) -> None:
    if os.name == 'posix':
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            logger.debug('Owned process group already exited: %s', proc.pid)
    else:
        # Windows development fallback; Linux production has group ownership.
        if proc.poll() is None:
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                           capture_output=True, timeout=10, check=False)
            proc.kill()


def run_supervised(args, *, timeout: float, capture_output: bool = True, **kwargs):
    if capture_output:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with subprocess.Popen(args, **process_group_options(), **kwargs) as proc:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
        finally:
            # Also remove descendants that outlive a normally exited launcher.
            terminate_process_tree(proc)
            proc.wait(timeout=10)
