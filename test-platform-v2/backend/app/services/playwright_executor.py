"""Playwright 测试执行器 — 子进程调用 npx playwright test，解析 JSON 报告。

使用 subprocess.Popen 实现进程管理、取消轮询、超时 kill 和产物隔离。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.db import SessionLocal

logger = logging.getLogger("playwright")

# ── 配置 ──
PLAYWRIGHT_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "playwright"
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "ui-runs"
DEFAULT_TIMEOUT = 300  # 5 minutes
MAX_CONCURRENT = 2  # 最大并发执行数
CANCEL_POLL_INTERVAL = 1.0  # 取消轮询间隔 (秒)

_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def _resolve_cmd(name: str) -> str | None:
    """跨平台解析可执行文件路径（Windows 上自动补全 .cmd/.exe 扩展名）。"""
    resolved = shutil.which(name)
    return resolved


def _check_playwright_installed() -> tuple[bool, str]:
    """检查 Playwright 是否可用。"""
    npx = _resolve_cmd("npx")
    if not npx:
        return False, "npx 命令不可用，请安装 Node.js"
    try:
        result = subprocess.run(
            [npx, "playwright", "--version"],
            capture_output=True, text=True, timeout=15,
            cwd=str(PLAYWRIGHT_DIR) if PLAYWRIGHT_DIR.exists() else os.getcwd(),
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"Playwright 未正确安装: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "检查 Playwright 版本超时"
    except Exception as e:
        return False, f"检查 Playwright 失败: {e}"


def _list_available_specs() -> list[str]:
    """列出可用的 Playwright 测试脚本。"""
    if not PLAYWRIGHT_DIR.exists():
        return []
    specs = []
    for f in PLAYWRIGHT_DIR.rglob("*.spec.js"):
        specs.append(str(f.relative_to(PLAYWRIGHT_DIR)).replace("\\", "/"))
    for f in PLAYWRIGHT_DIR.rglob("*.spec.ts"):
        specs.append(str(f.relative_to(PLAYWRIGHT_DIR)).replace("\\", "/"))
    return sorted(specs)


def run_playwright_test(db: Session, run_id: int, job_id: int, project_id: int) -> dict:
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

    job = db.get(UiTestJob, job_id)
    if not job:
        _fail_run(db, run, f"任务 #{job_id} 不存在")
        return {"error": f"任务 #{job_id} 不存在"}

    # 2. 标记 run 为 running，创建产物目录
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)

    artifact_dir = STORAGE_DIR / str(run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    run.artifact_dir = str(artifact_dir).replace("\\", "/")
    run.report_json_path = str(artifact_dir / "report.json").replace("\\", "/")
    run.cancel_requested = False
    db.commit()

    test_spec = (job.test_spec or "").strip()
    browser = (job.browser or "chromium").strip()

    # 3. 验证 test_spec 存在
    spec_path = PLAYWRIGHT_DIR / test_spec
    if not test_spec or not spec_path.exists():
        available = _list_available_specs()
        msg = f"测试脚本不存在: {test_spec or '(未指定)'}"
        if available:
            msg += f"。可用脚本: {', '.join(available[:10])}"
        return _fail_run(db, run, msg, job)

    # 4. 构建执行环境变量（注入 BASE_URL + Playwright 输出路径）
    env = os.environ.copy()
    base_url = (run.base_url or "").strip()
    if base_url:
        env["BASE_URL"] = base_url
        logger.info(f"Injecting BASE_URL={base_url} for run #{run_id}")
    # Playwright JSON 报告写入产物目录
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(artifact_dir / "report.json")

    npx = _resolve_cmd("npx")
    if not npx:
        return _fail_run(db, run, "npx 命令不可用，请安装 Node.js", job)

    # 5. 使用 subprocess.Popen 启动 Playwright 子进程
    cmd = [
        npx, "playwright", "test", test_spec,
        "--project", browser,
        "--reporter", "json",
        "--output", str(artifact_dir),
    ]
    logger.info(f"Running: {' '.join(cmd)} in {PLAYWRIGHT_DIR}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(PLAYWRIGHT_DIR),
            env=env,
        )

        # 记录进程 PID 以便取消时 kill
        run.process_id = proc.pid
        db.commit()
        logger.info(f"Playwright process started: PID={proc.pid}, run_id={run_id}")

        # 6. 轮询循环：检查进程状态 + 取消标记 + 超时
        start_time = time.monotonic()
        cancelled = False

        while proc.poll() is None:
            db.refresh(run)
            # 检查取消标记
            if run.cancel_requested or run.status == "cancelled":
                logger.info(f"Cancelling Playwright process PID={proc.pid} for run #{run_id}")
                proc.kill()
                stdout_text, stderr_text = _safe_communicate(proc)
                run.status = "cancelled"
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = "用户手动取消"
                run.stdout = stdout_text or ""
                run.stderr = (stderr_text or "")[:5000]
                cancelled = True
                break

            # 检查超时
            elapsed = time.monotonic() - start_time
            if elapsed > DEFAULT_TIMEOUT:
                logger.warning(f"Playwright timeout for run #{run_id} after {elapsed:.0f}s")
                proc.kill()
                stdout_text, stderr_text = _safe_communicate(proc)
                run.stdout = stdout_text or ""
                run.stderr = (stderr_text or "")[:5000]
                db.commit()
                return _fail_run(
                    db, run,
                    f"测试执行超时 ({DEFAULT_TIMEOUT}s)", job,
                )

            time.sleep(CANCEL_POLL_INTERVAL)

        if cancelled:
            db.commit()
            # Update job status on cancel
            if job.status == "running":
                job.status = "idle"
                db.commit()
            return {"status": "cancelled", "run_id": run_id}

        # 7. 进程正常结束，收集输出
        stdout_text, stderr_text = _safe_communicate(proc)
        run.stdout = stdout_text or ""
        run.stderr = (stderr_text or "")[:5000]

        exit_code = proc.returncode

        if exit_code != 0 and not (stdout_text or "").strip():
            # Playwright 自身错误（非测试失败，stdout 无 JSON 输出）
            return _fail_run(
                db, run,
                f"Playwright 执行失败 (exit={exit_code}): {(stderr_text or '')[:2000]}",
                job,
            )

        # 8. 解析 JSON 报告
        try:
            report = json.loads(stdout_text) if stdout_text else {}
        except json.JSONDecodeError:
            report = {}

        suites = report.get("suites", [])

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

        # 将 test-results 中的 Playwright 原生产物复制到隔离目录（方便查看，但只报告 artifact_dir 内的文件）
        test_results_dir = PLAYWRIGHT_DIR / "test-results"
        _copy_artifacts_to_run_dir(test_results_dir, artifact_dir)
        # Playwright trace 有时直接写在项目根目录，也复制进来
        _copy_artifacts_to_run_dir(PLAYWRIGHT_DIR, artifact_dir)

        # 检测 HTML 报告（如果存在）
        html_report = artifact_dir / "index.html"
        if html_report.exists():
            run.html_report_path = str(html_report).replace("\\", "/")

        return _complete_run(
            db, job, run,
            status="done" if fail_count == 0 else "fail",
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
    run.status = "fail"
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = message
    run.result = json.dumps({"error": message, "total": 0, "pass_": 0, "fail": 0, "skip": 0, "duration": 0}, ensure_ascii=False)
    if job:
        job.status = "fail"
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
        pass
    return items[:20]  # max 20


def _copy_artifacts_to_run_dir(src_dir: Path, dest_dir: Path) -> None:
    """将 src_dir 中的产物复制到 dest_dir（如果不在 dest_dir 中已存在）。"""
    if not src_dir.exists() or src_dir == dest_dir:
        return
    for pattern in ["*.png", "*.webm", "*.zip"]:
        for f in src_dir.rglob(pattern):
            # 跳过已在 artifact_dir 内的文件
            try:
                if str(dest_dir.resolve()) in str(f.resolve()):
                    continue
            except Exception:
                continue
            rel = f.relative_to(src_dir)
            dest = dest_dir / rel
            if not dest.exists():
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
                except Exception:
                    pass
