"""DeepSeek Harness runner 抽象 — Batch 172。

统一封装 dsh 执行：
- dsh_runtime=node：子进程调用 Node CLI headless（`node <dsh_harness_path> --profile headless <task>`），
  用于本地 Windows 开发（官方 Python SDK 持久 PTY 仅支持 POSIX）。
- dsh_runtime=python-sdk：官方 `deepseek-harness-sdk`（bundled runtime，无需 Node），用于生产 Linux 部署。

上层（ai_service / agent_orchestrator / dsh_task_service）只依赖
`run_dsh_task` 与 `runtime_available`，不感知运行时差异。执行结果统一为
`DshRunResult`；超时/失败/降级原因写入 `error`。
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# node runtime 默认入口（Windows 本地 dev 常用位置，可被 DSH_HARNESS_PATH 覆盖）
_DEFAULT_HARNESS_ENTRY = r"F:\deepseek-harness\apps\cli\lib\bin.js"


@dataclass
class DshRunResult:
    """一次 dsh 任务执行结果。"""

    final_response: str = ""
    exit_code: int = 0
    error: str = ""
    session_dir: str = ""
    timed_out: bool = False


class DshRunnerError(RuntimeError):
    """dsh 执行基础设施错误（配置/运行时缺失）。"""


def runtime_available() -> tuple[bool, str]:
    """返回 (是否可用, 不可用原因)。空原因 = 可用。"""
    reason = settings.dsh_unavailable_reason()
    if reason:
        return False, reason
    if settings.dsh_runtime == "node":
        entry = _node_entry()
        if not entry.exists():
            return False, f"DSH_HARNESS_PATH 不存在: {entry}"
        if not shutil.which("node"):
            return False, "未找到 node 可执行文件（PATH 中无 node）"
    return True, ""


def _node_entry() -> Path:
    configured = (settings.dsh_harness_path or "").strip()
    if configured:
        return Path(configured)
    default = Path(_DEFAULT_HARNESS_ENTRY)
    if default.exists():
        return default
    return default


def _session_root() -> Path:
    if settings.dsh_session_root:
        return Path(settings.dsh_session_root)
    # 默认：backend/storage/dsh-sessions
    return Path(__file__).resolve().parent.parent.parent.parent / "storage" / "dsh-sessions"


def _truncate(text: str, limit: int | None = None) -> str:
    limit = limit or settings.dsh_max_output_chars
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[输出已截断，共 {len(text)} 字符]"


def _workspace_for(workdir: str | None, session_root: Path) -> str:
    """返回本次任务的工作区：优先调用方指定，否则在 session_root 下建隔离工作区。"""
    if workdir:
        return workdir
    ws = (settings.dsh_workspace or "").strip()
    if ws:
        return ws
    isolated = session_root / "workspaces" / f"ws-{uuid.uuid4().hex[:10]}"
    isolated.mkdir(parents=True, exist_ok=True)
    return str(isolated)


def run_dsh_task(
    task: str,
    *,
    workspace: str | None = None,
    session_root: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    extra_env: dict[str, str] | None = None,
) -> DshRunResult:
    """执行一次 dsh 任务，返回结构化结果。任务文本为空或 DSH 不可用时快速失败。"""
    if not task or not task.strip():
        return DshRunResult(final_response="", exit_code=2, error="任务文本为空")
    available, reason = runtime_available()
    if not available:
        return DshRunResult(final_response="", exit_code=1, error=f"DSH 不可用: {reason}")

    resolved_model = model or settings.dsh_model or settings.ai_model
    resolved_timeout = timeout or settings.dsh_timeout_seconds
    sess_root = Path(session_root or str(_session_root()))
    try:
        sess_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - 环境异常
        return DshRunResult(final_response="", exit_code=1, error=f"无法创建会话目录 {sess_root}: {exc}")
    workdir = _workspace_for(workspace, sess_root)

    if settings.dsh_runtime == "python-sdk":
        return _run_python_sdk(
            task,
            workdir=workdir,
            session_root=sess_root,
            model=resolved_model,
            timeout=resolved_timeout,
            extra_env=extra_env,
        )
    return _run_node_cli(
        task,
        workdir=workdir,
        session_root=sess_root,
        model=resolved_model,
        timeout=resolved_timeout,
        extra_env=extra_env,
    )


def _run_node_cli(
    task: str,
    *,
    workdir: str,
    session_root: Path,
    model: str,
    timeout: float,
    extra_env: dict[str, str] | None,
) -> DshRunResult:
    """通过 Node CLI headless 执行任务（Windows 本地开发路径）。"""
    entry = _node_entry()
    cmd = ["node", str(entry), "--profile", "headless", task]
    env = os.environ.copy()
    env["DEEPSEEK_API_KEY"] = settings.dsh_api_key_effective
    if settings.dsh_base_url_effective:
        env["DEEPSEEK_BASE_URL"] = settings.dsh_base_url_effective
    env["DSH_MODEL"] = model
    env["DSH_SESSION_ROOT"] = str(session_root)
    if extra_env:
        env.update(extra_env)

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        logger.warning("dsh node runner timed out after %ss", timeout)
        return DshRunResult(
            final_response="",
            exit_code=124,
            error=f"dsh 执行超时（>{int(timeout)}s）",
            session_dir=str(session_root),
            timed_out=True,
        )
    except Exception as exc:  # pragma: no cover - 环境异常
        logger.exception("dsh node runner failed")
        return DshRunResult(final_response="", exit_code=1, error=str(exc), session_dir=str(session_root))

    elapsed = time.monotonic() - started
    stdout = _truncate((proc.stdout or "").strip())
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return DshRunResult(
            final_response=stdout,
            exit_code=proc.returncode,
            error=_truncate(stderr or f"dsh 退出码 {proc.returncode}"),
            session_dir=str(session_root),
        )
    logger.info("dsh node runner ok in %.1fs (exit 0)", elapsed)
    return DshRunResult(final_response=stdout, exit_code=0, session_dir=str(session_root))


def _run_python_sdk(
    task: str,
    *,
    workdir: str,
    session_root: Path,
    model: str,
    timeout: float,
    extra_env: dict[str, str] | None,
) -> DshRunResult:
    """通过官方 Python SDK 执行任务（生产 Linux 路径）。需要 deepseek-harness-sdk。"""
    try:
        from deepseek_harness import DeepSeekHarness
    except Exception as exc:  # pragma: no cover - 依赖缺失
        return DshRunResult(
            final_response="",
            exit_code=1,
            error=f"deepseek-harness-sdk 未安装或不可用: {exc}",
            session_dir=str(session_root),
        )

    cordis = (settings.dsh_cordis_config or "").strip()
    if cordis:
        cordis_path = Path(cordis)
    else:
        cordis_path = Path(__file__).resolve().parent / "minimal.cordis.yml"
    if not cordis_path.exists():
        return DshRunResult(
            final_response="",
            exit_code=1,
            error=f"DSH cordis 配置不存在: {cordis_path}",
            session_dir=str(session_root),
        )

    env = os.environ.copy()
    env["DEEPSEEK_API_KEY"] = settings.dsh_api_key_effective
    if settings.dsh_base_url_effective:
        env["DEEPSEEK_BASE_URL"] = settings.dsh_base_url_effective
    env["DSH_MODEL"] = model
    env["DSH_SESSION_ROOT"] = str(session_root)
    env["DSH_CWD"] = workdir
    if extra_env:
        env.update(extra_env)
    previous_env = {k: os.environ.get(k) for k in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DSH_MODEL", "DSH_SESSION_ROOT", "DSH_CWD")}
    for key, value in env.items():
        if key in previous_env:
            os.environ[key] = value

    session_id = f"platform-{uuid.uuid4().hex[:10]}"
    try:
        with DeepSeekHarness(
            provider="deepseek-official",
            model=model,
            max_tokens=49_152,
            cwd=workdir,
            session_root=str(session_root),
            cordis=str(cordis_path),
        ) as harness:
            result = harness.run(task, session_id=session_id)
        return DshRunResult(
            final_response=_truncate(result.final_response or ""),
            exit_code=0,
            session_dir=str(session_root),
        )
    except Exception as exc:  # pragma: no cover - 真实执行异常
        logger.exception("dsh python-sdk runner failed")
        return DshRunResult(
            final_response="",
            exit_code=1,
            error=_truncate(str(exc)),
            session_dir=str(session_root),
        )
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
