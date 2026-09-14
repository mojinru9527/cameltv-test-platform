"""Execution sandbox primitives for user-influenced Playwright processes.

This module does not claim OS-level container isolation. It removes accidental
secret inheritance and applies best-effort POSIX resource limits so a runner
can be migrated to a dedicated container later without changing call sites.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

from app.core.config import settings

# Keep only variables needed by Node, Playwright, Chromium and platform E2E.
# Never inherit the whole backend environment: it contains SECRET_KEY, DB and
# provider credentials.
_BASE_ENV_ALLOWLIST = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "PROGRAMDATA",
    "PLAYWRIGHT_BROWSERS_PATH",
    "PLAYWRIGHT_JSON_OUTPUT_NAME",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "NODE_OPTIONS",
}


def sandbox_environment(extra: Mapping[str, str | int | float | None] | None = None) -> dict[str, str]:
    """Build a minimal child environment from the host allowlist.

    ``extra`` is explicit caller intent and is copied after the allowlist. It is
    still the caller's responsibility to avoid passing secret material.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key in _BASE_ENV_ALLOWLIST and value
    }
    # CAMELTV_* is the documented platform E2E contract; keep only this prefix.
    env.update({
        key: value
        for key, value in os.environ.items()
        if key.startswith("CAMELTV_") and value and key.replace("_", "").isalnum()
    })
    if extra:
        for key, value in extra.items():
            if value is not None:
                env[str(key)] = str(value)
    return env


def _apply_posix_limits() -> None:
    """Best-effort limits executed in the child after fork and before exec."""
    if os.name != "posix":
        return
    import resource

    def limit(name: str, value: int) -> None:
        if not hasattr(resource, name):
            return
        rlimit = getattr(resource, name)
        try:
            current_soft, current_hard = resource.getrlimit(rlimit)
            modern = value if current_hard in (-1, resource.RLIM_INFINITY) else min(value, current_hard)
            if current_soft not in (-1, resource.RLIM_INFINITY):
                modern = min(modern, current_soft)
            resource.setrlimit(rlimit, (modern, modern))
        except (OSError, ValueError):
            # Some Docker/Windows-compatible runtimes do not expose every limit.
            pass

    limit("RLIMIT_CPU", settings.execution_cpu_limit_seconds)
    limit("RLIMIT_AS", settings.execution_memory_limit_mb * 1024 * 1024)
    limit("RLIMIT_FSIZE", settings.execution_file_size_limit_mb * 1024 * 1024)
    limit("RLIMIT_NOFILE", settings.execution_open_files_limit)
    limit("RLIMIT_NPROC", settings.execution_process_limit)


def execution_process_kwargs(extra_env: Mapping[str, str | int | float | None] | None = None) -> dict:
    """Return subprocess kwargs shared by all Playwright execution paths."""
    kwargs: dict = {"env": sandbox_environment(extra_env)}
    if os.name == "posix" and settings.execution_sandbox_enabled:
        kwargs["preexec_fn"] = _apply_posix_limits
    return kwargs
