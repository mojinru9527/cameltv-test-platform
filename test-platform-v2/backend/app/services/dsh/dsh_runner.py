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
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.ai_config_service import EffectiveAiConfig

logger = logging.getLogger(__name__)

# node runtime 默认入口（Windows 本地 dev 常用位置，可被 DSH_HARNESS_PATH 覆盖）
_DEFAULT_HARNESS_ENTRY = r"F:\deepseek-harness\apps\cli\lib\bin.js"

# ── Batch 184（C172-1/2）沙箱加固 ──
# 全局并发闸门：默认串行（安全优先），可经 DSH_MAX_CONCURRENT 上调。
_concurrency_gate = threading.BoundedSemaphore(max(1, int(getattr(settings, "dsh_max_concurrent", 1) or 1)))
# python-sdk 运行时通过 os.environ 传递凭据给 SDK（SDK 无显式凭据参数），
# 并发线程互改 env 会互相污染 → 用锁把「env 突变 + harness.run」序列化（C172-2）。
_python_sdk_env_lock = threading.Lock()


@dataclass
class DshRunResult:
    """一次 dsh 任务执行结果。"""

    final_response: str = ""
    exit_code: int = 0
    error: str = ""
    session_dir: str = ""
    timed_out: bool = False
    # Batch 191：本次任务的 ws-{uuid} 隔离工作区路径（终态 team.json 精确读取用；single 模式留空）
    workspace: str = ""


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
    """返回本次任务的**隔离**工作区（Batch 184 / C172-1）。

    无论是否配置共享 workspace，每个任务都分配到独立子目录 `{base}/ws-{uuid}`：
    - 调用方显式传 workdir → 该目录作为隔离根（在其下建 ws-{uuid}）；
    - 配置 DSH_WORKSPACE → 该目录作为隔离根；
    - 均无 → session_root/workspaces 作为隔离根。
    任务间文件互不可见，杜绝共享目录读写覆盖。
    """
    base = workdir or (settings.dsh_workspace or "").strip() or str(session_root / "workspaces")
    base_path = Path(base)
    isolated = base_path / f"ws-{uuid.uuid4().hex[:10]}"
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
    mode: str = "single",          # Batch 191：single | team（团队路由到 agent-team profile / team.cordis.yml）
    provider: EffectiveAiConfig | None = None,
    images: list[str] | None = None,  # 图片附件 file_id 列表（Batch fix：对齐 DSH web 贴图）
) -> DshRunResult:
    """执行一次 dsh 任务，返回结构化结果。

    Batch 184（C172-1）加固：
    - 任务文本超长直接拒绝（DSH_MAX_TASK_CHARS）；
    - 全局并发闸门（DSH_MAX_CONCURRENT，默认 1）限制同时在跑的任务数（排队不丢任务）。
    Batch 191（AgentTeams 团队模式）：
    - mode=team 时 node 走 --profile agent-team、python-sdk 走 team.cordis.yml，
      超时用 dsh_team_timeout_seconds（1800s）；沙箱语义（隔离工作区/闸门/配额）完全复用。
    """
    if not task or not task.strip():
        return DshRunResult(final_response="", exit_code=2, error="任务文本为空")
    if len(task) > settings.dsh_max_task_chars:
        return DshRunResult(
            final_response="",
            exit_code=2,
            error=f"任务文本超长（{len(task)} > {settings.dsh_max_task_chars} 字符上限，Batch 184 配额）",
        )
    available, reason = runtime_available()
    if not available:
        return DshRunResult(final_response="", exit_code=1, error=f"DSH 不可用: {reason}")

    resolved_model = model or (provider.model if provider else None) or settings.dsh_model or settings.ai_model
    if mode == "team":
        resolved_timeout = timeout or settings.dsh_team_timeout_seconds
    else:
        resolved_timeout = timeout or settings.dsh_timeout_seconds
    sess_root = Path(session_root or str(_session_root()))
    try:
        sess_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - 环境异常
        return DshRunResult(final_response="", exit_code=1, error=f"无法创建会话目录 {sess_root}: {exc}")

    # 并发闸门：超过 DSH_MAX_CONCURRENT 的任务排队等待（团队任务同样受控，C172-1 不回归）
    with _concurrency_gate:
        workdir = _workspace_for(workspace, sess_root)
        if images:
            # 图片附件：上传文件落任务工作区，并在任务文本末尾追加可读提示
            from app.services.dsh.dsh_attachment_service import image_hint, resolve_images

            paths = resolve_images(images, Path(workdir))
            hint = image_hint(paths)
            if hint:
                task = task + hint
        if settings.dsh_runtime == "python-sdk":
            return _run_python_sdk(
                task,
                workdir=workdir,
                session_root=sess_root,
                model=resolved_model,
                timeout=resolved_timeout,
                extra_env=extra_env,
                mode=mode,
                provider=provider,
            )
        return _run_node_cli(
            task,
            workdir=workdir,
            session_root=sess_root,
            model=resolved_model,
            timeout=resolved_timeout,
            extra_env=extra_env,
            mode=mode,
            provider=provider,
        )


def _run_node_cli(
    task: str,
    *,
    workdir: str,
    session_root: Path,
    model: str,
    timeout: float,
    extra_env: dict[str, str] | None,
    mode: str = "single",
    provider: EffectiveAiConfig | None = None,
) -> DshRunResult:
    """通过 Node CLI headless 执行任务（Windows 本地开发路径）。

    Batch 191：mode=team 时 --profile 用 dsh_team_profile（默认 agent-team）；
    profile 由 CLI 从 $DSH_HOME/profiles/ 解析（平台不传路径，见设计 §7.2）。
    """
    entry = _node_entry()
    profile_name = "headless" if mode != "team" else (settings.dsh_team_profile or "agent-team")
    cmd = ["node", str(entry), "--profile", profile_name, task]
    # 规范 §3.1：workspace 仅供团队模式终态 team.json 读取回传；single 留空（既有断言不回归）
    ws_field = workdir if mode == "team" else ""
    env = os.environ.copy()
    if provider is not None:
        env["DEEPSEEK_API_KEY"] = provider.api_key
        if provider.api_base_url:
            env["DEEPSEEK_BASE_URL"] = provider.api_base_url
    else:
        env["DEEPSEEK_API_KEY"] = settings.dsh_api_key_effective
        if settings.dsh_base_url_effective:
            env["DEEPSEEK_BASE_URL"] = settings.dsh_base_url_effective
    env["DSH_MODEL"] = model
    env["DSH_SESSION_ROOT"] = str(session_root)
    if mode == "team" and (settings.dsh_team_harness_path or "").strip():
        # Batch 191：dsh_team_harness_path 语义 = DSH_HOME 覆盖（profile 从 {path}/profiles/ 解析）
        env["DSH_HOME"] = settings.dsh_team_harness_path.strip()
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
            workspace=ws_field,
        )
    except Exception as exc:  # pragma: no cover - 环境异常
        logger.exception("dsh node runner failed")
        return DshRunResult(final_response="", exit_code=1, error=str(exc), session_dir=str(session_root), workspace=ws_field)

    elapsed = time.monotonic() - started
    stdout = _truncate((proc.stdout or "").strip())
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return DshRunResult(
            final_response=stdout,
            exit_code=proc.returncode,
            error=_truncate(stderr or f"dsh 退出码 {proc.returncode}"),
            session_dir=str(session_root),
            workspace=ws_field,
        )
    logger.info("dsh node runner ok in %.1fs (exit 0)", elapsed)
    return DshRunResult(final_response=stdout, exit_code=0, session_dir=str(session_root), workspace=ws_field)


def _run_python_sdk(
    task: str,
    *,
    workdir: str,
    session_root: Path,
    model: str,
    timeout: float,
    extra_env: dict[str, str] | None,
    mode: str = "single",
    provider: EffectiveAiConfig | None = None,
) -> DshRunResult:
    """通过官方 Python SDK 执行任务（生产 Linux 路径）。需要 deepseek-harness-sdk。"""
    # 规范 §3.1：workspace 仅供团队模式回传；single 留空
    ws_field = workdir if mode == "team" else ""
    try:
        from deepseek_harness import DeepSeekHarness
    except Exception as exc:  # pragma: no cover - 依赖缺失
        return DshRunResult(
            final_response="",
            exit_code=1,
            error=f"deepseek-harness-sdk 未安装或不可用: {exc}",
            session_dir=str(session_root),
            workspace=ws_field,
        )

    if mode == "team":
        cordis = (settings.dsh_team_cordis_config or "").strip()
        if cordis:
            cordis_path = Path(cordis)
        else:
            cordis_path = Path(__file__).resolve().parent / "team.cordis.yml"
    else:
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
            workspace=ws_field,
        )

    env = os.environ.copy()
    if provider is not None:
        env["DEEPSEEK_API_KEY"] = provider.api_key
        if provider.api_base_url:
            env["DEEPSEEK_BASE_URL"] = provider.api_base_url
    else:
        env["DEEPSEEK_API_KEY"] = settings.dsh_api_key_effective
        if settings.dsh_base_url_effective:
            env["DEEPSEEK_BASE_URL"] = settings.dsh_base_url_effective
    env["DSH_MODEL"] = model
    env["DSH_SESSION_ROOT"] = str(session_root)
    env["DSH_CWD"] = workdir
    if extra_env:
        env.update(extra_env)

    # Batch 184（C172-2）：SDK 从进程 env 读凭据，无显式传参口——
    # 「env 突变 + harness.run」整体持锁，杜绝多线程互改污染。
    with _python_sdk_env_lock:
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
                workspace=ws_field,
            )
        except Exception as exc:  # pragma: no cover - 真实执行异常
            logger.exception("dsh python-sdk runner failed")
            return DshRunResult(
                final_response="",
                exit_code=1,
                error=_truncate(str(exc)),
                session_dir=str(session_root),
                workspace=ws_field,
            )
        finally:
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
