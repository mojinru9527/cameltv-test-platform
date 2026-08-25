"""Playwright 测试执行器 — 子进程调用 npx playwright test，解析 JSON 报告。

使用 subprocess.Popen 实现进程管理、取消轮询、超时 kill 和产物隔离。
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.orm import Session


logger = logging.getLogger("playwright")

# ── 配置 ──
PLAYWRIGHT_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "playwright"
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "ui-runs"
# Batch 190: generated/ 下生成脚本的持久化副本目录（/app/storage 为持久卷；
# 容器重部署后 tests/playwright/generated 会被清空，执行器运行时从此处恢复）
GENERATED_SPECS_STORAGE = STORAGE_DIR.parent / "playground-specs"
DEFAULT_TIMEOUT = 300  # 5 minutes（历史默认；可经 UI_RUNNER_TIMEOUT_SECONDS 上调，见 _runner_timeout()）
MAX_CONCURRENT = 2  # 最大并发执行数
CANCEL_POLL_INTERVAL = 1.0  # 取消轮询间隔 (秒)

_semaphore = threading.BoundedSemaphore(MAX_CONCURRENT)
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _runner_timeout() -> float:
    """整任务超时（秒）：优先配置 ui_runner_timeout_seconds（默认 900），兜底常量 300。

    Batch 187：10 条用例的多 spec 生产回归实测约 3-5 分钟，硬编码 300s 会误杀
    正常运行；Railway 生产可经 env UI_RUNNER_TIMEOUT_SECONDS 按需调整。
    """
    try:
        from app.core.config import settings
        return max(float(settings.ui_runner_timeout_seconds), 60.0)
    except Exception:
        return float(DEFAULT_TIMEOUT)


def _runner_dir() -> Path:
    """解析 Playwright 运行根目录（C-UI-PROD-001）。

    优先级：
    1. 模块级 PLAYWRIGHT_DIR 被显式替换（测试/运维注入）→ 使用该值
    2. 配置 `UI_TEST_RUNNER_DIR`（settings.ui_test_runner_dir）非空：
       - 相对路径 → 相对 test-platform-v2 根（如 "tests/automation/ui"）
       - 绝对路径 → 直接使用
    3. 默认 → backend/tests/playwright（平台自测脚本）
    """
    from app.core.config import settings

    configured = (settings.ui_test_runner_dir or "").strip()
    if not configured:
        return PLAYWRIGHT_DIR
    p = Path(configured)
    if p.is_absolute():
        return p
    # __file__ = .../test-platform-v2/backend/app/services/playwright_executor.py
    # parent×3 = .../test-platform-v2/backend；再上一级 = test-platform-v2 根
    return Path(__file__).resolve().parent.parent.parent.parent / configured


def _claim_pending_run(db: Session, run_id: int) -> bool:
    """Atomically transition exactly one pending run to running.

    Batch 181（FIX-173-P2-06）：走 app.core.task_queue 统一原子认领原语
    （条件 UPDATE + rowcount），行为与原先一致。
    """
    from app.core.task_queue import QueueSpec, atomic_claim_by_id, utcnow
    from app.models.ui_test import UiTestRun

    _UI_RUN_QUEUE = QueueSpec(
        model=UiTestRun,
        id_col="id",
        status_col="status",
        pending="pending",
        running="running",
        failed="fail",
        lock_by_col="locked_by",
        lock_at_col="locked_at",
        order_col="id",
        order_asc=True,
    )
    claimed = atomic_claim_by_id(db, _UI_RUN_QUEUE, run_id, worker_id="ui-runner")
    if claimed is None:
        return False
    claimed.cancel_requested = False
    db.commit()
    return True


def _current_run_status(db: Session, run_id: int) -> str:
    from app.models.ui_test import UiTestRun

    run = db.get(UiTestRun, run_id, populate_existing=True)
    return run.status if run else "missing"


def _resolve_cmd(name: str) -> str | None:
    """跨平台解析可执行文件路径（Windows 上自动补全 .cmd/.exe 扩展名）。"""
    resolved = shutil.which(name)
    return resolved


def _check_playwright_installed() -> tuple[bool, str]:
    """检查 Playwright 是否可用。"""
    npx = _resolve_cmd("npx")
    if not npx:
        return False, "npx 命令不可用，请安装 Node.js"
    runner_dir = _runner_dir()
    local_test_package = runner_dir / "node_modules" / "@playwright" / "test" / "package.json"
    if not local_test_package.is_file():
        return False, (
            f"UI Runner 本地依赖未安装，请在 {runner_dir} 执行 npm ci"
        )
    try:
        result = subprocess.run(
            [npx, "playwright", "--version"],
            capture_output=True, text=True, timeout=15,
            cwd=str(runner_dir) if runner_dir.exists() else os.getcwd(),
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"Playwright 未正确安装: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "检查 Playwright 版本超时"
    except Exception as e:
        return False, f"检查 Playwright 失败: {e}"


def _list_available_specs() -> list[str]:
    """列出可用的 Playwright 测试脚本（跳过点开头的私有目录）。

    Batch 191: Playground 即时执行在 runner 内创建 .playground-tmp/ 工作目录，
    其中的临时 spec 不得混入可用脚本列表。
    """
    runner_dir = _runner_dir()
    if not runner_dir.exists():
        return []
    specs = []
    for f in runner_dir.rglob("*.spec.js"):
        rel = str(f.relative_to(runner_dir)).replace("\\", "/")
        if any(part.startswith(".") for part in rel.split("/")):
            continue
        specs.append(rel)
    for f in runner_dir.rglob("*.spec.ts"):
        rel = str(f.relative_to(runner_dir)).replace("\\", "/")
        if any(part.startswith(".") for part in rel.split("/")):
            continue
        specs.append(rel)
    return sorted(specs)


def _restore_generated_spec(runner_dir: Path, test_spec: str) -> bool:
    """从持久化存储恢复缺失的 generated/ 脚本（容器重部署后生成文件丢失）。

    Playground 回写生成的 spec 位于 runner 的 generated/ 目录（容器内临时
    文件系统），每次重新部署即被清空；持久化副本保存在
    GENERATED_SPECS_STORAGE（/app/storage/playground-specs，持久卷）。
    执行前发现缺失时自动恢复，避免 [Playground] UI 任务在重部署后全部报
    「测试脚本不存在」。
    """
    if not test_spec.startswith("generated/"):
        return False
    target = (runner_dir / test_spec).resolve()
    runner_root = runner_dir.resolve()
    if not target.is_relative_to(runner_root):
        return False
    stored = GENERATED_SPECS_STORAGE / Path(test_spec).name
    if not stored.is_file():
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(stored.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info("Restored generated spec %s from persistent storage", test_spec)
        return True
    except OSError:
        logger.exception("Failed to restore generated spec %s", test_spec)
        return False


def _resolve_environment_variables(db: Session, environment_id: int | None) -> dict[str, str]:
    """Return decrypted, shell-safe variables for the selected environment."""
    if not environment_id:
        return {}
    from sqlalchemy import select
    from app.core.cipher import decrypt_value
    from app.models.environment import EnvironmentVariable

    rows = db.scalars(
        select(EnvironmentVariable).where(EnvironmentVariable.environment_id == environment_id)
    ).all()
    resolved: dict[str, str] = {}
    for row in rows:
        if not _ENV_KEY_PATTERN.fullmatch(row.key or ""):
            logger.warning("Skipping invalid environment variable key for UI run: %r", row.key)
            continue
        value = row.value or ""
        if row.encrypted and value:
            try:
                value = decrypt_value(value)
            except Exception:
                logger.exception("Failed to decrypt UI-run environment variable %s", row.key)
                continue
        resolved[row.key] = value
    return resolved


def run_playwright_test(db: Session, run_id: int, job_id: int, project_id: int) -> dict:
    """Acquire a bounded slot and atomically claim a pending run before execution."""
    if not _semaphore.acquire(blocking=False):
        return {"status": _current_run_status(db, run_id), "run_id": run_id}

    try:
        if not _claim_pending_run(db, run_id):
            return {"status": _current_run_status(db, run_id), "run_id": run_id}
        from app.models.ui_test import UiTestJob
        from app.services.notify_service import queue_notification

        job = db.get(UiTestJob, job_id)
        task_name = job.name if job else f"UI 任务 #{job_id}"
        queue_notification(
            project_id,
            "task_started",
            {
                "task_type": "UI 自动化",
                "task_name": task_name,
                "triggered_by": f"user#{job.creator_id}" if job else "-",
                "link": "/uitest",
            },
        )
        output = _run_playwright_test(db, run_id, job_id, project_id)
        result = output.get("result") or {}
        passed = int(result.get("pass_", 0) or 0)
        failed = int(result.get("fail", 0) or 0)
        skipped = int(result.get("skip", 0) or 0)
        total = int(result.get("total", passed + failed + skipped) or 0)
        status = output.get("status", "failed")
        queue_notification(
            project_id,
            "task_finished",
            {
                "task_type": "UI 自动化",
                "task_name": task_name,
                "status": status,
                "result_summary": f"通过 {passed} / 失败 {failed} / 跳过 {skipped}",
                "link": "/uitest",
            },
        )
        queue_notification(
            project_id,
            "test_result",
            {
                "task_name": task_name,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": f"{round(passed * 100 / total, 1)}%" if total else "0%",
                "conclusion": "通过" if total and failed == 0 else status,
                "link": "/uitest",
            },
        )
        return output
    finally:
        _semaphore.release()


def _run_playwright_test(db: Session, run_id: int, job_id: int, project_id: int) -> dict:
    """使用 subprocess.Popen 执行 Playwright 测试，支持取消轮询和超时 kill。

    所有代码路径（成功/失败/取消/超时）都会更新 run 状态和 error_message。
    此函数由后台 worker 调用，使用独立 db session。
    """
    from app.models.ui_test import UiTestJob, UiTestRun

    # 1. 加载已有的 run 和 job
    run = db.get(UiTestRun, run_id)
    if not run:
        logger.error(f"UiTestRun #{run_id} 不存在")
        return {"error": f"运行记录 #{run_id} 不存在"}

    # Cancellation can win after the CAS claim but before executor setup.
    if run.status != "running":
        return {"status": run.status, "run_id": run_id}

    job = db.get(UiTestJob, job_id)
    if not job:
        _fail_run(db, run, f"任务 #{job_id} 不存在")
        return {"error": f"任务 #{job_id} 不存在"}

    # 2. The wrapper already claimed this run; create its isolated artifact directory.
    artifact_dir = STORAGE_DIR / str(run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    run.artifact_dir = str(artifact_dir).replace("\\", "/")
    run.report_json_path = str(artifact_dir / "report.json").replace("\\", "/")
    db.commit()

    test_spec = (job.test_spec or "").strip()
    browser = (job.browser or "chromium").strip()
    runner_dir = _runner_dir()

    # 3. 验证 test_spec 存在（防路径穿越：spec 必须位于 runner 目录内）
    spec_path = (runner_dir / test_spec).resolve()
    runner_root = runner_dir.resolve()
    if not test_spec or not spec_path.is_relative_to(runner_root):
        available = _list_available_specs()
        msg = f"测试脚本不存在: {test_spec or '(未指定)'}"
        if available:
            msg += f"。可用脚本: {', '.join(available[:10])}"
        return _fail_run(db, run, msg, job)

    # Batch 190: 容器重部署后 generated/ 下生成脚本会被清空（Playground 回写
    # 产物），缺失时先从持久化存储恢复；恢复失败才按脚本缺失处理。
    if not spec_path.exists() and not _restore_generated_spec(runner_dir, test_spec):
        available = _list_available_specs()
        msg = f"测试脚本不存在: {test_spec or '(未指定)'}"
        if available:
            msg += f"。可用脚本: {', '.join(available[:10])}"
        return _fail_run(db, run, msg, job)

    # 4. 构建执行环境变量（注入 BASE_URL + CAMELTV_BASE_URL + 环境变量 + CAMELTV_* 透传 + 输出路径）
    env = os.environ.copy()
    base_url = (run.base_url or "").strip()
    if base_url:
        env["BASE_URL"] = base_url
        # B14：业务 E2E 脚本读取 CAMELTV_BASE_URL（preconditions.ts），
        # 仅注入 BASE_URL 会导致契约变量缺失而 BlockedRunError。二者同时注入，缺失契约变量时诚实报错。
        env["CAMELTV_BASE_URL"] = base_url
        logger.info(f"Injecting BASE_URL/CAMELTV_BASE_URL={base_url} for run #{run_id}")
    env.update(_resolve_environment_variables(db, job.environment_id))
    # CAMELTV_* 前缀变量透传（业务 E2E preconditions 依赖；如 CAMELTV_TARGET_ENV/
    # CAMELTV_RUN_LEVEL/AD_BLOCK_DOMAINS 等），便于平台环境注入驱动外部 E2E 脚本
    env.update({
        k: v for k, v in os.environ.items()
        if k.startswith("CAMELTV_") and _ENV_KEY_PATTERN.fullmatch(k)
    })
    # Playwright JSON 报告写入产物目录
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(artifact_dir / "report.json")

    npx = _resolve_cmd("npx")
    if not npx:
        return _fail_run(db, run, "npx 命令不可用，请安装 Node.js", job)

    # 5. 使用 subprocess.Popen 启动 Playwright 子进程
    cmd = [
        npx, "playwright", "test", str(spec_path.relative_to(runner_root)),
        "--project", browser,
        "--reporter", "json",
        "--output", str(artifact_dir),
    ]
    logger.info(f"Running: {' '.join(cmd)} in {runner_dir}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(runner_dir),
            env=env,
        )

        # 记录进程 PID 以便取消时 kill
        run.process_id = proc.pid
        db.commit()
        logger.info(f"Playwright process started: PID={proc.pid}, run_id={run_id}")

        # Drain both pipes immediately. Waiting for process exit before reading
        # can deadlock once a JSON report fills the OS pipe buffer.
        process_output: dict[str, str] = {"stdout": "", "stderr": ""}

        def _drain_process_output() -> None:
            try:
                stdout_value, stderr_value = proc.communicate()
                process_output["stdout"] = stdout_value or ""
                process_output["stderr"] = stderr_value or ""
            except Exception as exc:
                process_output["stderr"] = f"读取 Playwright 输出失败: {type(exc).__name__}: {exc}"

        output_thread = threading.Thread(target=_drain_process_output, daemon=True)
        output_thread.start()

        # 6. 轮询循环：检查进程状态 + 取消标记 + 超时
        start_time = time.monotonic()
        cancelled = False

        while proc.poll() is None:
            db.refresh(run)
            # 检查取消标记
            if run.cancel_requested or run.status == "cancelled":
                logger.info(f"Cancelling Playwright process PID={proc.pid} for run #{run_id}")
                proc.kill()
                output_thread.join(timeout=10)
                stdout_text = process_output["stdout"]
                stderr_text = process_output["stderr"]
                run.status = "cancelled"
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = "用户手动取消"
                run.stdout = stdout_text or ""
                run.stderr = (stderr_text or "")[:5000]
                cancelled = True
                break

            # 检查超时
            elapsed = time.monotonic() - start_time
            run_timeout = _runner_timeout()
            if elapsed > run_timeout:
                logger.warning(f"Playwright timeout for run #{run_id} after {elapsed:.0f}s")
                proc.kill()
                output_thread.join(timeout=10)
                stdout_text = process_output["stdout"]
                stderr_text = process_output["stderr"]
                run.stdout = stdout_text or ""
                run.stderr = (stderr_text or "")[:5000]
                db.commit()
                return _fail_run(
                    db, run,
                    f"测试执行超时 ({run_timeout:.0f}s)", job,
                )

            time.sleep(CANCEL_POLL_INTERVAL)

        if cancelled:
            db.commit()
            # Update job status on cancel
            if job.status == "running":
                job.status = "pending"
                db.commit()
            return {"status": "cancelled", "run_id": run_id}

        # 7. 进程正常结束，收集输出
        output_thread.join(timeout=10)
        if output_thread.is_alive():
            proc.kill()
            return _fail_run(db, run, "Playwright 输出读取线程未能结束", job)
        stdout_text = process_output["stdout"]
        stderr_text = process_output["stderr"]
        run.stdout = stdout_text or ""
        run.stderr = (stderr_text or "")[:5000]

        exit_code = proc.returncode
        report = _load_playwright_json_report(artifact_dir, stdout_text)

        if exit_code != 0 and report is None:
            # A non-zero exit is a normal test failure when a valid JSON report
            # exists. Without one, Playwright itself failed before reporting.
            return _fail_run(
                db, run,
                f"Playwright 执行失败 (exit={exit_code}): {(stderr_text or '')[:2000]}",
                job,
            )

        # 8. Parse the isolated JSON report; successful no-report runs retain
        # the historical zero-test result instead of becoming executor errors.
        suites = (report or {}).get("suites", [])

        # Recursively flatten nested suites → specs (Playwright JSON can nest suites arbitrarily)
        def _collect_specs(suite_list: list[dict]) -> list[dict]:
            result: list[dict] = []
            for s in suite_list:
                result.extend(s.get("specs", []))
                result.extend(_collect_specs(s.get("suites", [])))
            return result

        specs_list = _collect_specs(suites)

        total = 0
        passed = 0
        fail_count = 0
        skipped = 0
        duration = 0

        for spec in specs_list:
            for test in spec.get("tests", []):
                total += 1
                results_list = test.get("results", [])
                if not results_list:
                    skipped += 1
                    continue
                last_result = results_list[-1]
                status = last_result.get("status", "skipped")
                duration += last_result.get("duration", 0)
                if status in ("passed", "expected"):
                    passed += 1
                elif status in ("failed", "unexpected"):
                    fail_count += 1
                elif status == "skipped":
                    skipped += 1

        duration_sec = round(duration / 1000, 2) if duration else 0

        # 9. 产物隔离：只从 artifact_dir 收集产物，不扫描共享目录
        screenshots = _collect_artifacts(artifact_dir, "*.png")
        videos = _collect_artifacts(artifact_dir, "*.webm")
        traces = _collect_artifacts(artifact_dir, "*.zip")

        # 检测 HTML 报告（如果存在）
        html_report = artifact_dir / "index.html"
        if html_report.exists():
            run.html_report_path = str(html_report).replace("\\", "/")

        return _complete_run(
            db, job, run,
            status="passed" if fail_count == 0 else "failed",
            total=total, passed=passed, failed=fail_count, skipped=skipped,
            duration=duration_sec,
            screenshots=screenshots,
            videos=videos,
            traces=traces,
        )

    except Exception as e:
        logger.exception(f"Playwright run error for run #{run_id}, job #{job_id}")
        return _fail_run(
            db, run,
            f"执行异常: {type(e).__name__}: {e}", job,
        )


# ── Helpers ──

def _load_playwright_json_report(artifact_dir: Path, stdout_text: str) -> dict | None:
    """Load a valid report from this run's directory, then fall back to stdout."""
    report_path = artifact_dir / "report.json"
    if report_path.is_file():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict) and isinstance(payload.get("suites"), list):
                return payload
        except (OSError, UnicodeError, json.JSONDecodeError):
            logger.warning("Invalid Playwright JSON report: %s", report_path)

    if stdout_text and stdout_text.strip():
        try:
            payload = json.loads(stdout_text)
            if isinstance(payload, dict) and isinstance(payload.get("suites"), list):
                return payload
        except json.JSONDecodeError:
            logger.warning("Playwright 报告 JSON 解析失败")

    return None

def _safe_communicate(proc: subprocess.Popen) -> tuple[str, str]:
    """安全地读取子进程 stdout/stderr，防止管道死锁。"""
    try:
        stdout_text, stderr_text = proc.communicate(timeout=10)
        return stdout_text or "", stderr_text or ""
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            stdout_text, stderr_text = proc.communicate()
            return stdout_text or "", stderr_text or ""
        except Exception:
            return "", ""
    except Exception:
        return "", ""


def _fail_run(db: Session, run, message: str, job=None) -> dict:
    """标记 run 为失败并落库 error_message。所有失败路径必须调用此函数。"""
    run.status = "failed"
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = message
    run.result = json.dumps({"error": message, "total": 0, "pass_": 0, "fail": 0, "skip": 0, "duration": 0}, ensure_ascii=False)
    if job:
        job.status = "failed"
        job.last_result = json.dumps({"error": message}, ensure_ascii=False)
    db.commit()
    db.refresh(run)

    # 知识库回流：UI 测试失败 → 沉淀为知识切片
    try:
        project_id = job.project_id if job else 0
        from app.services.knowledge import ingest_service
        ingest_service.ingest_ui_test_failure_in_new_session(project_id, run.id)
    except Exception:
        logger.exception("Failed to ingest UI test failure for run #%s", run.id)
    return {
        "id": run.id, "job_id": run.job_id, "status": "fail",
        "result": {"error": message},
        "screenshots": [], "video_url": run.video_url, "trace_id": run.trace_id,
        "started_at": run.started_at, "finished_at": run.finished_at,
        "error_message": message,
    }


def _complete_run(
    db: Session,
    job,
    run,
    *,
    status: str,
    total: int, passed: int, failed: int, skipped: int, duration: float,
    screenshots: list[str] | None = None,
    videos: list[str] | None = None,
    traces: list[str] | None = None,
    error: str | None = None,
) -> dict:
    """完成一次运行，更新 run 和 job 状态。所有正常/异常结束路径调用此函数。"""
    result = {
        "total": total, "pass_": passed, "fail": failed,
        "skip": skipped, "duration": duration,
    }
    if error:
        result["error"] = error

    run.result = json.dumps(result, ensure_ascii=False)
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = error or ""
    run.screenshots = json.dumps(screenshots or [], ensure_ascii=False)
    if videos:
        run.video_url = videos[0]
    if traces:
        run.trace_id = traces[0]

    job.last_result = json.dumps(result, ensure_ascii=False)
    job.status = status

    db.commit()
    db.refresh(run)

    return {
        "id": run.id, "job_id": run.job_id, "status": status,
        "result": result, "screenshots": screenshots or [],
        "video_url": run.video_url, "trace_id": run.trace_id,
        "error_message": run.error_message or "",
        "started_at": run.started_at, "finished_at": run.finished_at,
    }


def _collect_artifacts(base_dir: Path, pattern: str) -> list[str]:
    """收集产物路径（仅从指定目录，不扫描共享目录）。"""
    items = []
    try:
        if not base_dir.exists():
            return items
        for f in base_dir.rglob(pattern):
            items.append(str(f.relative_to(base_dir)).replace("\\", "/"))
    except Exception:
        logger.warning("Playwright 产物文件列表读取失败，返回部分结果（最多 20 项）")
    return items[:20]  # max 20
