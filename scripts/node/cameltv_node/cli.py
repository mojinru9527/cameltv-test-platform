"""cameltv-node —— CamelTv 本地执行节点 CLI（Batch 258 / B1-5）。

一条命令开工：
    cameltv-node up --node-id my-pc --capabilities api web

它做四件事（全部在**本机**完成，控制面不执行任何浏览器/模型动作）：
    1) 注册/复用节点身份（节点令牌，仅返回一次，存 ~/.cameltv-node.json）
    2) 心跳续租（执行中每 30s 一次，租约默认 300s）
    3) 认领本项目的 ExecutionJob，拉取载荷并真实执行（api=httpx / web=Playwright）
    4) 上传证据（sha256 manifest 对账）→ 上报结果

**诚实原则**：依赖缺失、执行失败、上传失败一律如实上报/打印；断网时保持心跳重试，
不谎报失败——任务会因租约过期被平台回收为 pending，节点恢复后可再次认领。

**自愈原则（C269-3）**：平台**可达但报错**（HTTP 4xx/5xx、业务码 != 0）与断网同属「可恢复」，
轮询循环退避重试而不是退进程；只有连续失败超过上限才退出非零（退出前必留 stderr + 日志文件），
让 supervisor 能重启。已认领的任务只重试、不丢弃：租约由心跳续租，平台回收后节点才放手。
节点 stderr 一律双写日志文件（默认 `~/.cameltv-node/logs/cameltv-node.log`），
避免再出现「进程消失但没有日志可回看」。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

import httpx

# 允许两种入口：`python scripts/node/cameltv_node/cli.py` 与 `python -m cameltv_node.cli`
if __package__ in (None, ""):  # pragma: no cover - 取决于调用方式
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cameltv_node import evidence, executor  # noqa: E402

CONFIG_PATH = Path.home() / ".cameltv-node.json"
DEFAULT_BASE = "https://swiftbugs.cn"
DEFAULT_HEARTBEAT_SECONDS = 30

# 退出码：0 成功 / 1 任务结论为失败 / 2 用法或配置错误 / 3 执行器依赖缺失 /
# 4 平台侧失败（连续失败达上限，或 `--once` 单轮内失败）——4 是 C269-3 新增，交 supervisor 重启。
EXIT_PLATFORM_ERROR = 4

# 平台故障自愈参数（C269-3）：连续失败上限只用于把「平台长期不可用」交出去，不影响单次抖动重试。
DEFAULT_MAX_CONSECUTIVE_FAILURES = 10
DEFAULT_BACKOFF_BASE_SECONDS = 5.0
DEFAULT_MAX_BACKOFF_SECONDS = 60.0

# 节点 stderr 必须落盘（Batch 269 的退出事故无法逐帧回看，就是因为只留在当时的控制台里）。
DEFAULT_LOG_PATH = Path.home() / ".cameltv-node" / "logs" / "cameltv-node.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

_LOGGER = logging.getLogger("cameltv-node")
_LOGGER.propagate = False
_LOG_PATH: Path | None = None


def log_file_path() -> Path | None:
    """当前生效的日志文件；未落盘（仅 stderr）时返回 None。"""
    return _LOG_PATH


def setup_logging(log_path: str | Path | None = None) -> Path | None:
    """诊断输出同时写 stderr 与日志文件（按大小轮转，安全追加）。

    默认 `~/.cameltv-node/logs/cameltv-node.log`，可用 `--log-file` / `CAMELTV_NODE_LOG_FILE`
    覆盖；路径不可写时降级为仅 stderr（记一条警告），绝不因此让节点起不来。
    """
    global _LOG_PATH
    for handler in list(_LOGGER.handlers):
        _LOGGER.removeHandler(handler)
        handler.close()
    _LOGGER.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    _LOGGER.addHandler(stream)

    _LOG_PATH = None
    target = Path(log_path).expanduser() if log_path else DEFAULT_LOG_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            target, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        _LOGGER.addHandler(file_handler)
        _LOG_PATH = target
    except OSError as exc:
        _LOGGER.warning("日志文件不可用（%s）：%s；本次仅写 stderr", target, exc)
    return _LOG_PATH


def _ensure_logging() -> None:
    """直接调用（未走 main）时也要保证 stderr/文件双写。"""
    if not _LOGGER.handlers:
        setup_logging()


def log_info(message: str) -> None:
    _ensure_logging()
    _LOGGER.info(message)


def log_warn(message: str) -> None:
    _ensure_logging()
    _LOGGER.warning(message)


def log_error(message: str) -> None:
    _ensure_logging()
    _LOGGER.error(message)


def _install_excepthook() -> None:
    """真 bug（未捕获异常）的 traceback 也要落盘，不能只留在控制台里。"""
    previous = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, exc_value, exc_tb)
            return
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip()
        log_error(f"未捕获异常（真 bug，不是平台故障）：\n{detail}")
        previous(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


class TransportDown(RuntimeError):
    """平台不可达（断网/网络抖动）：调用方应重试而不是判定任务失败。"""


class PlatformError(RuntimeError):
    """平台**可达**但拒绝了本次调用（HTTP 4xx/5xx 或业务码 != 0）。

    C269-3：这类失败同样是**可恢复**的（平台重启窗口、瞬时 5xx、令牌轮换），
    轮询循环退避重试；只有连续失败超过上限才退出（退出前必留可读日志）。
    """

    def __init__(self, message: str, *, status_code: int = 0, code=None):
        super().__init__(message)
        self.status_code = int(status_code or 0)
        self.code = code

    @property
    def auth_problem(self) -> bool:
        """凭据/权限类（401/403）：可重试，但日志里要给出排查方向。"""
        return self.status_code in (401, 403)


class JobGone(PlatformError):
    """本节点已不再持有该任务（平台按租约回收或改派）：停止对该任务的重试。

    这不算丢任务：平台侧已把任务放回 `pending`，节点只是不再重复上报。
    """


# 循环内一律按「可恢复」处理的异常（C269-3 的核心约束）
RECOVERABLE_ERRORS = (TransportDown, PlatformError)


def load_config() -> dict:
    cfg = {
        "base_url": os.environ.get("CAMELTV_BASE_URL", DEFAULT_BASE),
        "node_id": os.environ.get("CAMELTV_NODE_ID", ""),
        "token": os.environ.get("CAMELTV_NODE_TOKEN", ""),
        "jwt": os.environ.get("CAMELTV_JWT", ""),
        "project_id": os.environ.get("CAMELTV_PROJECT_ID", ""),
    }
    if CONFIG_PATH.exists():
        try:
            stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update({key: value for key, value in stored.items() if value})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def call(
    cfg: dict,
    method: str,
    path: str,
    *,
    body=None,
    params=None,
    use_node_token: bool = True,
    files=None,
    timeout: float = 300,
):
    headers: dict[str, str] = {}
    if cfg.get("project_id"):
        headers["X-Project-Id"] = str(cfg["project_id"])
    if use_node_token and cfg.get("token"):
        headers["X-AI-Agent-Token"] = cfg["token"]
    if cfg.get("jwt"):
        headers["Authorization"] = f"Bearer {cfg['jwt']}"
    if files is None:
        headers["Content-Type"] = "application/json"
    url = cfg["base_url"].rstrip("/") + "/api/v1" + path
    try:
        resp = httpx.request(
            method, url, headers=headers, json=body, params=params, files=files, timeout=timeout
        )
    except httpx.TransportError as exc:
        raise TransportDown(f"平台不可达: {type(exc).__name__}: {exc}") from exc
    try:
        payload = resp.json()
    except ValueError:
        payload = {"code": resp.status_code, "msg": resp.text[:300]}
    if resp.status_code >= 400 or payload.get("code") not in (None, 0):
        # C269-3：这里曾经 `raise SystemExit(2)` —— 平台一次 500/403 就让节点进程无声消失、
        # 已认领/待认领的任务滞留 pending。现在只抛可恢复的 PlatformError，由调用方退避重试。
        raise PlatformError(
            f"{method} {path} -> HTTP {resp.status_code} code={payload.get('code')} "
            f"msg={payload.get('msg') or payload.get('detail')}",
            status_code=resp.status_code,
            code=payload.get("code"),
        )
    return payload.get("data", payload)


def _job_call(cfg: dict, method: str, path: str, *, job_id: int, **kwargs):
    """任务域调用：404 = 平台已回收/改派该任务，转成 JobGone 让循环停止对它重试。"""
    try:
        return call(cfg, method, path, **kwargs)
    except PlatformError as exc:
        if exc.status_code == 404:
            raise JobGone(
                f"任务 {job_id} 已不在本节点名下（平台已回收或改派）: {exc}",
                status_code=exc.status_code,
                code=exc.code,
            ) from exc
        raise


# ── 身份 ───────────────────────────────────────────────────────

def cmd_login(args, cfg) -> int:
    password = args.password or os.environ.get("CAMELTV_PASSWORD", "")
    if not password:
        import getpass

        password = getpass.getpass("请输入平台密码: ")
    url = cfg["base_url"].rstrip("/") + "/api/v1/auth/login"
    try:
        resp = httpx.post(url, json={"username": args.username, "password": password}, timeout=60)
    except httpx.TransportError as exc:
        log_error(f"平台不可达: {exc}")
        return 2
    payload = resp.json() if resp.content else {}
    token = (payload.get("data") or {}).get("access_token") or ""
    if not token:
        log_error(
            f"登录失败 -> HTTP {resp.status_code} msg={payload.get('msg') or payload.get('detail')}"
        )
        return 2
    cfg["jwt"] = token
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    save_config(cfg)
    print(json.dumps({"ok": True, "username": args.username, "saved_to": str(CONFIG_PATH)}, ensure_ascii=False))
    return 0


def cmd_register(args, cfg) -> int:
    if not cfg.get("jwt"):
        log_error("缺少平台登录态，请先执行 login --username <账号>")
        return 2
    data = call(
        cfg,
        "POST",
        "/ai/agents/register",
        body={"agent_id": args.node_id, "capabilities": args.capabilities},
        use_node_token=False,
    )
    cfg["node_id"] = data.get("agent_id") or args.node_id
    cfg["token"] = data.get("token") or cfg.get("token", "")
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    save_config(cfg)
    print(
        json.dumps(
            {
                "node_id": cfg["node_id"],
                "project_scope": data.get("project_scope"),
                "token_saved_to": str(CONFIG_PATH),
                "notice": data.get("token_notice"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_doctor(args, cfg) -> int:
    report = {
        "base_url": cfg["base_url"],
        "node_id": cfg.get("node_id"),
        "project_id": cfg.get("project_id"),
        "token_configured": bool(cfg.get("token")),
    }
    try:
        status = call(cfg, "GET", "/execution-jobs/node-status")
        report["node_status"] = status
        report["ok"] = True
    except PlatformError as exc:
        report["ok"] = False
        report["error"] = f"节点状态查询失败（检查项目上下文与 execution:view 权限）: {exc}"
    except TransportDown as exc:
        report["ok"] = False
        report["error"] = str(exc)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


# ── 任务流转 ───────────────────────────────────────────────────

def _claim(cfg: dict) -> dict | None:
    data = call(cfg, "POST", "/execution-jobs/claim", body={"node_id": cfg["node_id"]})
    return data or None


def _fetch_payload(cfg: dict, job_id: int) -> dict:
    return _job_call(
        cfg,
        "GET",
        f"/execution-jobs/{job_id}/payload",
        job_id=job_id,
        params={"node_id": cfg["node_id"]},
    )


def _heartbeat_once(cfg: dict, job_id: int) -> bool:
    try:
        _job_call(
            cfg,
            "POST",
            f"/execution-jobs/{job_id}/heartbeat",
            job_id=job_id,
            body={"node_id": cfg["node_id"]},
        )
        return True
    except RECOVERABLE_ERRORS:
        return False


class HeartbeatThread(threading.Thread):
    """执行期间续租；断网只记录，不把任务判死（租约到期由平台回收）。"""

    def __init__(self, cfg: dict, job_id: int, interval: float):
        super().__init__(daemon=True)
        self._cfg = cfg
        self._job_id = job_id
        self._interval = max(5.0, float(interval))
        # 注意：不能命名成 `_stop` —— threading.Thread 内部有同名方法，
        # 覆盖它会让解释器在收尾时调用我们的 Event 对象 → TypeError: not callable。
        self._stop_event = threading.Event()
        self.lost = False

    def run(self) -> None:
        while not self._stop_event.wait(self._interval):
            ok = _heartbeat_once(self._cfg, self._job_id)
            if not ok:
                self.lost = True
                log_warn(f"心跳失败（job {self._job_id}），任务可能被判超时回收")

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=5)


def _upload_evidence(cfg: dict, job_id: int, directory: Path) -> dict:
    files = evidence.collect_files(directory)
    local = evidence.local_manifest(files)
    multipart = [("files", (name, data, "application/octet-stream")) for name, data in files]
    remote = _job_call(
        cfg,
        "POST",
        f"/execution-jobs/{job_id}/evidence",
        job_id=job_id,
        params={"node_id": cfg["node_id"]},
        files=multipart,
        timeout=600,
    )
    problems = evidence.verify_against(remote, local)
    if problems:
        raise RuntimeError("证据上传对账失败: " + "; ".join(problems))
    return remote


def _execute(cfg: dict, job: dict, payload: dict, work_dir: Path) -> dict:
    kind = job.get("kind")
    cases = (payload.get("payload") or {}).get("cases") or []
    base_url = (payload.get("payload") or {}).get("base_url") or ""
    if not cases:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "all_pass": False,
            "cases": [],
            "error": "任务载荷不含任何用例",
        }
    try:
        if kind == "api":
            return executor.run_api_cases(cases, evidence_dir=work_dir, base_url=base_url)
        if kind == "web":
            return executor.run_web_cases(cases, evidence_dir=work_dir, base_url=base_url)
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "all_pass": False,
            "cases": [],
            "error": f"未知任务类型: {kind}",
        }
    except executor.ExecutorUnavailable as exc:
        return {
            "total": len(cases),
            "passed": 0,
            "failed": len(cases),
            "all_pass": False,
            "cases": [],
            "error": str(exc),
        }


def _run_job(cfg: dict, job: dict, *, work_root: Path) -> tuple[dict, Path]:
    """执行阶段：拉载荷 → 真实执行 → 本地落盘 results.json。

    平台错误（含 404 = 任务已被回收）原样上抛，由 `_process_job` 决定退避重试还是放手。
    """
    job_id = job["id"]
    work_dir = work_root / f"job-{job_id}-attempt-{job.get('attempt', 1)}"
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"[job {job_id}] kind={job.get('kind')} attempt={job.get('attempt')} env={job.get('env_ref')}")
    payload = _fetch_payload(cfg, job_id)
    results = _execute(cfg, job, payload, work_dir)
    (work_dir / executor.RESULT_FILE).write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return results, work_dir


def _report_job(cfg: dict, job: dict, work_dir: Path, results: dict) -> dict:
    """上报阶段：上传证据 + 上报结论。平台错误上抛后**只重发结论，不重跑用例**。"""
    job_id = job["id"]
    uploaded = 0
    upload_error = ""
    if results.get("cases"):
        try:
            manifest = _upload_evidence(cfg, job_id, work_dir)
            uploaded = int(manifest.get("file_count", 0))
        except RuntimeError as exc:
            # 证据上传失败不阻塞结论上报（诚实原则：把失败写进 result/error_message）
            upload_error = str(exc)
            log_warn(f"[job {job_id}] 证据上传失败: {upload_error}")
    status = "completed" if results.get("all_pass") else "failed"
    summary = (
        f"{results.get('passed', 0)}/{results.get('total', 0)} pass"
        + (f" | {results['error']}" if results.get("error") else "")
    )
    _job_call(
        cfg,
        "POST",
        f"/execution-jobs/{job_id}/report",
        job_id=job_id,
        body={
            "node_id": cfg["node_id"],
            "status": status,
            "summary": summary,
            "result": {
                "total": results.get("total", 0),
                "passed": results.get("passed", 0),
                "failed": results.get("failed", 0),
                "evidence_files": uploaded,
                "upload_error": upload_error,
                "error": results.get("error", ""),
            },
            "error_message": results.get("error", "") or upload_error,
        },
    )
    print(f"[job {job_id}] {status} — {summary}（证据 {uploaded} 个文件）")
    return {"job_id": job_id, "status": status, "summary": summary, "evidence_files": uploaded}


def _sleep(seconds: float) -> None:
    """退避等待；单独成函数便于测试注入（不在单测里真睡）。"""
    time.sleep(seconds)


def _failure_budget(args) -> int:
    """连续失败上限（0 = 不限）。"""
    return max(0, int(getattr(args, "max_consecutive_failures", DEFAULT_MAX_CONSECUTIVE_FAILURES)))


def _backoff_seconds(consecutive: int, args) -> float:
    """指数退避 + 抖动（等量抖动），单次上限可配：5s → 10s → 20s → 40s → 60s…"""
    base = max(0.1, float(getattr(args, "backoff_base_seconds", DEFAULT_BACKOFF_BASE_SECONDS)))
    cap = max(base, float(getattr(args, "max_backoff_seconds", DEFAULT_MAX_BACKOFF_SECONDS)))
    ceiling = min(cap, base * (2 ** max(0, consecutive - 1)))
    return ceiling / 2 + random.uniform(0.0, ceiling / 2)


def _describe(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, PlatformError) and exc.auth_problem:
        text += "（凭据/权限类失败：请检查节点令牌、X-Project-Id 与 execution:view 权限）"
    return text


def _give_up(consecutive: int, what: str, exc: BaseException, *, holding: dict | None = None) -> int:
    """连续失败达上限：退出非零并说明原因（交 supervisor 重启），退出前必留日志。"""
    message = (
        f"{what} 连续失败 {consecutive} 次：{_describe(exc)}；"
        f"退出码 {EXIT_PLATFORM_ERROR}（平台侧故障，不是任务失败）"
    )
    if holding:
        message += (
            f"；任务 {holding['id']} 仍在本节点名下，租约到期后平台会自动回收为 pending，"
            "节点重启后可再次认领（任务不会丢）"
        )
    log_error(message)
    return EXIT_PLATFORM_ERROR


def _retry_or_give_up(
    exc: BaseException,
    *,
    args,
    phase: str,
    job: dict,
    consecutive: int,
    budget: int,
    hint: str,
) -> int | None:
    """可恢复失败：留日志 + 退避后重试（返回 None）；`--once` 或达上限则返回退出码。"""
    if args.once:
        log_error(f"--once：单轮{phase}任务 {job['id']} 失败，退出（{_describe(exc)}）")
        return EXIT_PLATFORM_ERROR
    if budget and consecutive >= budget:
        return _give_up(consecutive, f"{phase}任务 {job['id']}", exc, holding=job)
    delay = _backoff_seconds(consecutive, args)
    log_warn(
        f"[job {job['id']} {phase}重试 {consecutive}/{budget or '∞'}] {_describe(exc)}；"
        f"{delay:.1f}s 后重试{hint}"
    )
    _sleep(delay)
    return None


def _process_job(cfg: dict, job: dict, *, args, work_root: Path, budget: int) -> int | None:
    """处理一个已认领任务：平台错误只退避重试**同一任务**，绝不丢弃。

    任务已认领 → 本节点持有租约。拉载荷/上报失败都重试同一任务（心跳持续续租），
    直到上报成功，或平台明确回 404（已回收/改派，任务回到 pending，不算丢）。
    返回需要退出的退出码；None = 本轮任务已闭环。
    """
    job_id = job["id"]
    consecutive = 0
    heartbeat = HeartbeatThread(cfg, job_id, args.heartbeat_seconds)
    heartbeat.start()
    try:
        # ── 执行阶段 ──
        while True:
            try:
                results, work_dir = _run_job(cfg, job, work_root=work_root)
                break
            except JobGone as exc:
                log_warn(f"[job {job_id}] {exc}；平台已把任务放回 pending，本节点放手（不是丢弃）")
                return None
            except RECOVERABLE_ERRORS as exc:
                consecutive += 1
                code = _retry_or_give_up(
                    exc,
                    args=args,
                    phase="执行",
                    job=job,
                    consecutive=consecutive,
                    budget=budget,
                    hint="同一任务（任务仍在本节点名下，不会滞留 pending）",
                )
                if code is not None:
                    return code
        # ── 上报阶段：只重发结论，不重跑用例 ──
        while True:
            try:
                result = _report_job(cfg, job, work_dir, results)
                break
            except JobGone as exc:
                log_warn(f"[job {job_id}] {exc}；平台已把任务放回 pending，本节点放手（不是丢弃）")
                return None
            except RECOVERABLE_ERRORS as exc:
                consecutive += 1
                code = _retry_or_give_up(
                    exc,
                    args=args,
                    phase="上报",
                    job=job,
                    consecutive=consecutive,
                    budget=budget,
                    hint="（执行结果已在本地，不会重跑用例）",
                )
                if code is not None:
                    return code
        if heartbeat.lost:
            log_warn(f"[job {job_id}] 执行期间心跳失败过，结论已上报但平台可能已按超时处理")
        log_info(f"[job {job_id}] {result['status']} — {result['summary']}（证据 {result['evidence_files']} 个文件）")
        return None
    finally:
        heartbeat.stop()


def _loop(cfg: dict, args) -> int:
    work_root = Path(args.work_dir).expanduser()
    work_root.mkdir(parents=True, exist_ok=True)
    idle = 0
    consecutive = 0
    budget = _failure_budget(args)
    log_info(
        f"cameltv-node up — node={cfg['node_id']} base={cfg['base_url']} work={work_root} "
        f"连续失败上限={budget or '不限'} 日志={log_file_path() or '未落盘（仅 stderr）'}"
    )
    while True:
        try:
            job = _claim(cfg)
        except RECOVERABLE_ERRORS as exc:
            consecutive += 1
            if args.once:
                log_error(f"--once：单轮认领失败，退出（{_describe(exc)}）")
                return EXIT_PLATFORM_ERROR
            if budget and consecutive >= budget:
                return _give_up(consecutive, "认领任务", exc)
            delay = _backoff_seconds(consecutive, args)
            log_warn(
                f"[认领重试 {consecutive}/{budget or '∞'}] {_describe(exc)}；"
                f"{delay:.1f}s 后重试（任务不会被判失败）"
            )
            _sleep(delay)
            continue
        consecutive = 0
        if not job:
            idle += 1
            if idle % 10 == 1:
                log_info("[idle] 暂无待执行任务")
            if args.once:
                return 0
            _sleep(args.poll_seconds)
            continue
        idle = 0
        code = _process_job(cfg, job, args=args, work_root=work_root, budget=budget)
        if code is not None:
            return code
        if args.once:
            return 0
        _sleep(args.poll_seconds)


# ── 离线执行/上传 ──────────────────────────────────────────────

def cmd_run_api(args, cfg) -> int:
    return _run_offline(args, cfg, kind="api")


def cmd_run_web(args, cfg) -> int:
    return _run_offline(args, cfg, kind="web")


def _run_offline(args, cfg, *, kind: str) -> int:
    out = Path(args.out).expanduser()
    if args.job_file:
        spec = json.loads(Path(args.job_file).read_text(encoding="utf-8"))
    elif args.job:
        spec = _fetch_payload(cfg, args.job)
    else:
        log_error("需要 --job <id> 或 --job-file <payload.json>")
        return 2
    payload = spec.get("payload") or {}
    cases = payload.get("cases") or []
    base_url = args.base_url or payload.get("base_url") or ""
    runner = executor.run_api_cases if kind == "api" else executor.run_web_cases
    try:
        results = runner(cases, evidence_dir=out, base_url=base_url)
    except executor.ExecutorUnavailable as exc:
        log_error(str(exc))
        return 3
    (out / executor.RESULT_FILE).write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in results.items() if k != "cases"}, ensure_ascii=False))
    return 0 if results.get("all_pass") else 1


def cmd_upload(args, cfg) -> int:
    manifest = _upload_evidence(cfg, args.job, Path(args.dir).expanduser())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def cmd_show(args, cfg) -> int:
    print(json.dumps(call(cfg, "GET", f"/execution-jobs/{args.job}"), ensure_ascii=False, indent=2))
    return 0


# ── 入口 ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cameltv-node", description="CamelTv 本地执行节点（控制面不执行）")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="登录平台并保存会话（注册节点需要）")
    login.add_argument("--username", required=True)
    login.add_argument("--password", default=os.environ.get("CAMELTV_PASSWORD", ""))
    login.add_argument("--project-id", type=int, default=0)
    login.set_defaults(func=cmd_login)

    reg = sub.add_parser("register", help="注册/复用本地节点并签发节点令牌")
    reg.add_argument("--node-id", required=True)
    reg.add_argument("--project-id", type=int, default=0)
    reg.add_argument("--capabilities", nargs="*", default=["api", "web"])
    reg.set_defaults(func=cmd_register)

    doctor = sub.add_parser("doctor", help="平台连通性、凭据与节点状态自检")
    doctor.set_defaults(func=cmd_doctor)

    up = sub.add_parser("up", help="一条命令开工：注册+心跳+认领循环")
    up.add_argument("--node-id", default="")
    up.add_argument("--capabilities", nargs="*", default=["api", "web"])
    up.add_argument("--project-id", type=int, default=0)
    up.add_argument("--work-dir", default=str(Path.cwd() / "cameltv-node-evidence"))
    up.add_argument("--poll-seconds", type=float, default=5.0)
    up.add_argument("--heartbeat-seconds", type=float, default=DEFAULT_HEARTBEAT_SECONDS)
    up.add_argument("--once", action="store_true", help="只跑一轮（CI/自检用）")
    up.add_argument(
        "--log-file",
        default="",
        help=f"诊断日志落盘路径（默认 {DEFAULT_LOG_PATH}，也可用 CAMELTV_NODE_LOG_FILE）",
    )
    up.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=os.environ.get("CAMELTV_NODE_MAX_FAILURES") or DEFAULT_MAX_CONSECUTIVE_FAILURES,
        help=(
            "平台连续失败上限，达到即退出非零交 supervisor 重启（0 = 不限；"
            f"默认 {DEFAULT_MAX_CONSECUTIVE_FAILURES}，也可用 CAMELTV_NODE_MAX_FAILURES）"
        ),
    )
    up.add_argument(
        "--backoff-base-seconds",
        type=float,
        default=DEFAULT_BACKOFF_BASE_SECONDS,
        help=f"平台失败退避基数秒，指数增长（默认 {DEFAULT_BACKOFF_BASE_SECONDS:g}）",
    )
    up.add_argument(
        "--max-backoff-seconds",
        type=float,
        default=DEFAULT_MAX_BACKOFF_SECONDS,
        help=f"单次退避上限秒（默认 {DEFAULT_MAX_BACKOFF_SECONDS:g}）",
    )
    up.set_defaults(func=cmd_up)

    api = sub.add_parser("run-api", help="本地执行接口用例（httpx）")
    api.add_argument("--job", type=int, default=0)
    api.add_argument("--job-file", default="")
    api.add_argument("--out", default="./evidence")
    api.add_argument("--base-url", default="")
    api.set_defaults(func=cmd_run_api)

    web = sub.add_parser("run-web", help="本地执行 Web 用例（Playwright）")
    web.add_argument("--job", type=int, default=0)
    web.add_argument("--job-file", default="")
    web.add_argument("--out", default="./evidence")
    web.add_argument("--base-url", default="")
    web.set_defaults(func=cmd_run_web)

    upload = sub.add_parser("upload", help="上传证据目录（sha256 manifest 对账）")
    upload.add_argument("--job", type=int, required=True)
    upload.add_argument("--dir", required=True)
    upload.set_defaults(func=cmd_upload)

    show = sub.add_parser("show", help="查看任务详情")
    show.add_argument("--job", type=int, required=True)
    show.set_defaults(func=cmd_show)
    return parser


def cmd_up(args, cfg) -> int:
    """`up` 可自带 node-id/capabilities：缺身份时自动注册（一条命令开工）。"""
    if args.node_id:
        cfg["node_id"] = args.node_id
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    if not cfg.get("node_id"):
        log_error("未配置 node_id，请执行 register --node-id <名字> 或传 --node-id")
        return 2
    if not cfg.get("token"):
        if not cfg.get("jwt"):
            log_error("未配置节点令牌，且无平台登录态可自动注册：请先 login")
            return 2
        data = call(
            cfg,
            "POST",
            "/ai/agents/register",
            body={"agent_id": cfg["node_id"], "capabilities": args.capabilities},
            use_node_token=False,
        )
        cfg["token"] = data.get("token") or ""
        save_config(cfg)
        print(f"[init] 已注册节点 {cfg['node_id']} 并保存令牌到 {CONFIG_PATH}")
    return _loop(cfg, args)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(getattr(args, "log_file", "") or os.environ.get("CAMELTV_NODE_LOG_FILE", ""))
    _install_excepthook()
    cfg = load_config()
    if args.command not in ("login", "register", "up") and not cfg.get("node_id"):
        log_error("未配置 node_id，请先执行 register")
        return 2
    try:
        return args.func(args, cfg)
    except RECOVERABLE_ERRORS as exc:
        log_error(_describe(exc))
        return EXIT_PLATFORM_ERROR
    except KeyboardInterrupt:
        log_warn("已停止心跳；任务将因租约过期回到 pending，可重新认领")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
