"""Execution sandbox primitives for user-influenced Playwright processes.

**边界声明（Batch 259 / B2-1，H1）——先说清楚"这层不是什么"：**

- 本模块**不宣称**具备 OS/内核级隔离。它做的是**进程内可达面收敛**：
  环境变量白名单（子进程拿不到 SECRET_KEY / DB 口令 / provider token）、
  best-effort POSIX 资源上限（CPU/内存/文件大小/句柄/进程数）。
- **文件系统与网络的内核级隔离属于部署层**：容器、只读挂载、网络命名空间或节点侧
  出网代理。本模块只把出网白名单（`execution_egress_allowlist` → `CAMELTV_EGRESS_ALLOWLIST`）
  作为**唯一事实源**下发给子进程与节点，避免白名单出现第二处实现。
- **非 root 运行**同样是部署层要求（容器 user / systemd 用户），不在进程内解决。
- 生成代码的危险 API 由 `app/core/spec_guard.py` 在**执行前**静态拦截——
  静态检查也不是沙箱，两者互不替代（与 B2-3 纠正的「dry-run 不是沙箱」同一原则）。

这样划分的目的：任何读到这段注释的人都能准确知道"哪一层负责什么"，
不会把"执行路径已经过沙箱"当成既成事实。
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
    # 出网白名单：进程内不阻断网络，但把唯一事实源交给子进程/节点侧执行者，
    # 避免"配置在平台、执行靠另外一份清单"的双份漂移。
    allowlist = (settings.execution_egress_allowlist or "").strip()
    if allowlist:
        env["CAMELTV_EGRESS_ALLOWLIST"] = allowlist
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
