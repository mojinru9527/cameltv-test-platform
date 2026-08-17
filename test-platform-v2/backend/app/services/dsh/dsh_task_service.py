"""DSH 任务执行服务 — Batch 172。

提交/查询/取消 + 后台 worker（DB 认领，多 worker 可消费，模式对齐 ai_tasks.py）。
worker 执行时调用 dsh_runner.run_dsh_task，状态与输出落库。

Batch 181（FIX-173-P2-06）：认领/回收/循环骨架收敛到 app.core.task_queue 统一原语；
模型补 locked_at/locked_by 列（20260816_b181_task_queue_locks），
started_at 不再兼作锁字段。

Batch 191（AgentTeams 团队模式）：
- execute_task 按 task.mode 分派；mode=team 走团队分支：
  执行线程跑 run_dsh_task(mode="team", persona 经 DSH_SYSTEM_PROMPT 注入)，
  轮询线程（间隔 dsh_team_poll_seconds）扫描 ws-{uuid} 隔离工作区下的
  .agent-teams/<teamId>/team.json，用独立短 SessionLocal 全量幂等写
  task.team_json（R-3：绝不与执行线程共享 session）；执行结束用
  DshRunResult.workspace 精确路径读终态快照。
- 状态沿用 single 词表（pending/running/success/failed/cancelled）；
  团队任务取消语义不变（仅 pending，C191-2 登记 running 取消延后）。
"""
from __future__ import annotations

import json
import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.task_queue import (
    QueueSpec,
    QueueWorkerLoop,
    atomic_claim,
    utcnow,
)
from app.models.dsh_task import DshTask

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

_STALE_CLAIM_SECONDS = 300

_DSH_QUEUE = QueueSpec(
    model=DshTask,
    id_col="id",
    status_col="status",
    pending="pending",
    running="running",
    failed="failed",
    lock_by_col="locked_by",
    lock_at_col="locked_at",
    order_col="created_at",
    order_asc=True,
)

_loop = QueueWorkerLoop(name="dsh-task-worker", poll_interval=1.0, on_tick=lambda: _poll_once())


def _now() -> datetime:
    return utcnow()


def submit_task(
    db,
    *,
    project_id: int,
    task: str,
    params: dict | None = None,
    mode: str = "single",
    operator_id: int = 0,
) -> DshTask:
    """插入 pending 任务并唤醒 worker（多 worker 部署下任何进程均可认领）。"""
    row = DshTask(
        project_id=project_id,
        task=task,
        status="pending",
        params_json=json.dumps(params or {}, ensure_ascii=False),
        operator_id=operator_id,
        mode=mode,
        team_json="{}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    ensure_worker_running()
    _loop.kick()
    return row


def list_tasks(
    db,
    project_id: int,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DshTask], int]:
    from sqlalchemy import func

    stmt = select(DshTask).where(DshTask.project_id == project_id)
    cnt = select(func.count(DshTask.id)).where(DshTask.project_id == project_id)
    if status:
        stmt = stmt.where(DshTask.status == status)
        cnt = cnt.where(DshTask.status == status)
    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(DshTask.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_task(db, task_id: int, project_id: int) -> DshTask | None:
    row = db.get(DshTask, task_id)
    if not row or row.project_id != project_id:
        return None
    return row


def cancel_task(db, task_id: int, project_id: int) -> DshTask | None:
    """仅 pending 可取消。返回更新后的任务或 None（不存在/不可取消）。"""
    row = db.get(DshTask, task_id)
    if not row or row.project_id != project_id:
        return None
    if row.status != "pending":
        return None
    row.status = "cancelled"
    row.finished_at = _now()
    db.commit()
    db.refresh(row)
    return row


def claim_next_task(db, now: datetime | None = None) -> DshTask | None:
    """认领最早 pending 任务（stale 锁可重认领），Batch 181 起走统一原语。"""
    return atomic_claim(db, _DSH_QUEUE, worker_id="dsh-worker", stale_seconds=_STALE_CLAIM_SECONDS)


def execute_task(db, task: DshTask, runner=None) -> None:
    """执行已认领任务并写回结果/错误。runner 可注入用于测试。

    Batch 191：按 task.mode 分派——single 走现状同步路径；team 走
    `_execute_team`（执行线程 + 轮询线程，线程安全铁律见模块 docstring）。
    """
    from app.services.dsh.dsh_runner import run_dsh_task

    runner = runner or run_dsh_task
    try:
        params = {}
        try:
            params = json.loads(task.params_json or "{}")
        except json.JSONDecodeError:
            params = {}
        if task.mode == "team":
            _execute_team(db, task, params, runner)
            return
        result = runner(task.task, workspace=params.get("workspace") or None)
        task.status = "success" if result.exit_code == 0 else "failed"
        task.output_text = (result.final_response or "")[:20000]
        task.error = (result.error or "")[:2000] if result.exit_code != 0 else ""
        task.session_dir = result.session_dir
        task.finished_at = _now()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 任务失败写回
        task.status = "failed"
        task.error = str(exc)[:2000]
        task.finished_at = _now()
        db.commit()


# ── Batch 191：团队模式执行（线程安全铁律 R-3）──────────────────────────

def _team_isolation_root(params: dict) -> Path:
    """与 dsh_runner._workspace_for 相同的隔离根规则（设计 §4.3）。"""
    from app.services.dsh.dsh_runner import _session_root

    base = (
        (params.get("workspace") or "").strip()
        or (settings.dsh_workspace or "").strip()
        or str(_session_root() / "workspaces")
    )
    return Path(base)


def _find_team_json_path(root: Path) -> str | None:
    """隔离根扫描：`{root}/ws-*/` 下所有 `.agent-teams/<teamId>/team.json`。

    返回 mtime 最新的可解析 team.json 路径；解析失败（半写/损坏）跳过该目录。
    调用方在轮询线程内锁定首次命中路径（此后只读该路径，防并发任务串扰）。
    """
    if not root.is_dir():
        return None
    candidates: list[Path] = []
    try:
        for ws_dir in root.glob("ws-*"):
            if not ws_dir.is_dir():
                continue
            team_root = ws_dir / ".agent-teams"
            if not team_root.is_dir():
                continue
            for tj in team_root.glob("*/team.json"):
                try:
                    data = json.loads(tj.read_text(encoding="utf-8", errors="replace"))
                    if isinstance(data, dict) and data.get("id"):
                        candidates.append(tj)
                except (json.JSONDecodeError, OSError):
                    continue
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0])


def _truncate_team_snapshot(raw: str) -> str:
    """team_json 快照截断（PRD §5 / 设计 §4.3）：上限 dsh_max_output_chars。

    超长时截断并在快照内加 `_truncated: true` 标记；截断后仍是合法 JSON。
    """
    limit = settings.dsh_max_output_chars
    if len(raw) <= limit:
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    if isinstance(data, dict):
        data["_truncated"] = True
    out = json.dumps(data, ensure_ascii=False)
    if len(out) > limit:
        # 极端情况：加了标记仍超长 → 只保留骨架（前端显示「进度数据已截断」）
        out = json.dumps({"_truncated": True, "_note": "团队进度数据超长已截断"}, ensure_ascii=False)
    return out


def _team_poller(task_id: int, stop_event: threading.Event, poll_seconds: float, root: Path) -> None:
    """轮询线程：扫描隔离根 team.json，独立短 SessionLocal 全量幂等写 team_json。

    - 每次写库用独立短 SessionLocal，绝不使用 execute_task 的认领 session（R-3）；
    - team_json 全量幂等覆盖（无增量合并）；单轮失败（文件占用/解析失败）记录后下轮重试；
    - 首次成功解析的路径锁定，此后只读该路径。
    """
    locked_path: str | None = None
    while not stop_event.wait(poll_seconds):
        try:
            if locked_path is None:
                locked_path = _find_team_json_path(root)
                if locked_path is None:
                    continue  # 团队尚未建队（无快照），下轮再扫
            try:
                raw = Path(locked_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue  # 文件暂不可读，下轮重试
            snapshot = _truncate_team_snapshot(raw)
            with SessionLocal() as s:
                row = s.get(DshTask, task_id)
                if row is None:
                    continue
                row.team_json = snapshot
                s.commit()
        except Exception as exc:  # noqa: BLE001 - 单轮失败不退出轮询
            logger.warning("DSH team poller error (task %s): %s", task_id, exc)


def _team_runner(
    task_text: str,
    params: dict,
    persona: str,
    result_box: queue.Queue,
    runner,
) -> None:
    """执行线程：跑 run_dsh_task(mode="team")，结果经线程安全队列传回。

    不碰任何 DB session（R-3）；异常兜底为 failed 结果（与 single 一致）。
    """
    try:
        result = runner(
            task_text,
            workspace=params.get("workspace") or None,
            mode="team",
            timeout=settings.dsh_team_timeout_seconds,
            extra_env={"DSH_SYSTEM_PROMPT": persona},
        )
        result_box.put(result)
    except Exception as exc:  # noqa: BLE001 - 执行线程异常兜底
        from app.services.dsh.dsh_runner import DshRunResult

        logger.warning("DSH team runner thread error: %s", exc)
        result_box.put(DshRunResult(final_response="", exit_code=1, error=f"团队执行线程异常: {exc}"))


def _execute_team(db, task: DshTask, params: dict, runner) -> None:
    """团队模式执行：执行线程 + 轮询线程 + 终态快照（设计 §4.2/§4.3）。"""
    from app.services.dsh.agent_team_persona import build_agent_team_persona
    from app.services.dsh.dsh_runner import DshRunResult

    batch_mode = params.get("batch_mode", "full")
    persona = build_agent_team_persona(task.task, batch_mode)
    result_box: queue.Queue = queue.Queue(maxsize=1)
    stop_event = threading.Event()
    root = _team_isolation_root(params)

    # 线程启动前捕获纯数据（执行线程不碰 ORM 对象）
    task_text = task.task
    poll_seconds = settings.dsh_team_poll_seconds

    t_exec = threading.Thread(
        target=_team_runner,
        args=(task_text, params, persona, result_box, runner),
        daemon=True,
    )
    t_poll = threading.Thread(
        target=_team_poller,
        args=(task.id, stop_event, poll_seconds, root),
        daemon=True,
    )
    t_exec.start()
    t_poll.start()

    # 防御性兜底：join 超时后强制终止轮询，执行结果可能未产生
    t_exec.join(timeout=settings.dsh_team_timeout_seconds + 60)
    stop_event.set()
    t_poll.join(timeout=5)

    if result_box.empty():
        result = DshRunResult(final_response="", exit_code=1, error="团队执行线程异常终止（未知原因）")
    else:
        result = result_box.get()

    # 终态：用 result.workspace 精确路径再读一次 team.json（无扫描歧义）
    if result.workspace:
        try:
            ws_root = Path(result.workspace)
            team_root = ws_root / ".agent-teams"
            if team_root.is_dir():
                candidates = sorted(
                    team_root.glob("*/team.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    raw = candidates[0].read_text(encoding="utf-8", errors="replace")
                    task.team_json = _truncate_team_snapshot(raw)
        except OSError as exc:  # pragma: no cover - 终态读取异常不阻断状态落库
            logger.warning("DSH team final snapshot read failed: %s", exc)

    task.status = "success" if result.exit_code == 0 else "failed"
    task.output_text = (result.final_response or "")[:20000]
    task.error = (result.error or "")[:2000] if result.exit_code != 0 else ""
    task.session_dir = result.session_dir
    task.finished_at = _now()
    db.commit()


def _process_claimed(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(DshTask, task_id)
        if task is None or task.status != "running":
            return
        execute_task(db, task)
    finally:
        db.close()


def _poll_once() -> None:
    """单次轮询：原子认领一条任务并提交到执行池。"""
    db = SessionLocal()
    try:
        task = claim_next_task(db)
        if task is not None:
            _executor.submit(_process_claimed, task.id)
    except Exception as exc:  # noqa: BLE001 - 轮询失败不退出
        logger.warning("DSH task worker poll error: %s", exc)
    finally:
        db.close()


def ensure_worker_running() -> None:
    """启动后台轮询线程（幂等）。"""
    _loop.start()


def shutdown_worker(timeout: float = 5.0) -> None:
    """优雅关闭 worker 线程（测试/退出用）。"""
    _loop.shutdown(timeout=timeout)
