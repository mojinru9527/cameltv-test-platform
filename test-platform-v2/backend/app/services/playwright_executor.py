"""Playwright 测试执行器 — 子进程调用 npx playwright test，解析 JSON 报告。"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.db import SessionLocal

logger = logging.getLogger("playwright")

# ── 配置 ──
PLAYWRIGHT_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "playwright"
DEFAULT_TIMEOUT = 300  # 5 minutes
MAX_CONCURRENT = 2  # 最大并发执行数

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


def run_playwright_test(db: Session, job_id: int, project_id: int) -> dict:
    """在后台线程中执行 Playwright 测试（同步子进程）。

    此函数由 BackgroundTasks 调用，使用独立 db session。
    """
    from app.models.ui_test import UiTestJob, UiTestRun

    # 1. 检查 Playwright 可用性
    pw_ok, pw_msg = _check_playwright_installed()
    if not pw_ok:
        return _fail_job(db, job_id, f"Playwright 不可用: {pw_msg}")

    # 2. 加载任务
    job = db.query(UiTestJob).filter(
        UiTestJob.id == job_id, UiTestJob.project_id == project_id
    ).first()
    if not job:
        return {"error": "任务不存在"}

    test_spec = (job.test_spec or "").strip()
    browser = (job.browser or "chromium").strip()

    # 3. 验证 test_spec
    spec_path = PLAYWRIGHT_DIR / test_spec
    if not test_spec or not spec_path.exists():
        available = _list_available_specs()
        msg = f"测试脚本不存在: {test_spec or '(未指定)'}"
        if available:
            msg += f"。可用脚本: {', '.join(available[:10])}"
        return _fail_job(db, job_id, msg)

    # 4. 创建运行记录
    now = datetime.now(timezone.utc)
    run = UiTestRun(job_id=job_id, status="running", started_at=now)
    db.add(run)
    db.flush()

    try:
        # 5. 执行 Playwright
        npx = _resolve_cmd("npx")
        if not npx:
            return _complete_run(
                db, job, run, status="fail",
                total=0, passed=0, failed=0, skipped=0, duration=0,
                error="npx 命令不可用",
            )
        cmd = [
            npx, "playwright", "test", test_spec,
            "--project", browser,
            "--reporter", "json",
        ]
        logger.info(f"Running: {' '.join(cmd)} in {PLAYWRIGHT_DIR}")

        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=DEFAULT_TIMEOUT,
            cwd=str(PLAYWRIGHT_DIR),
        )

        # 6. 解析结果
        if result.returncode != 0 and not result.stdout.strip():
            # Playwright 自身错误（非测试失败）
            stderr = result.stderr[:1000] if result.stderr else ""
            return _complete_run(
                db, job, run, status="fail",
                total=0, passed=0, failed=0, skipped=0, duration=0,
                error=f"Playwright 执行失败 (exit={result.returncode}): {stderr}",
            )

        # Parse JSON report
        try:
            report = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            report = {}

        suites = report.get("suites", [])
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        duration = 0

        # Flatten suite → spec → test hierarchy
        specs_list = []
        for suite in suites:
            for spec in suite.get("specs", []):
                specs_list.append(spec)

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
                if status == "passed" or status == "expected":
                    passed += 1
                elif status == "failed" or status == "unexpected":
                    failed += 1
                elif status == "skipped":
                    skipped += 1

        duration_sec = round(duration / 1000, 2) if duration else 0

        # 7. 收集产物
        screenshots = _collect_artifacts(PLAYWRIGHT_DIR, "*.png")
        videos = _collect_artifacts(PLAYWRIGHT_DIR, "*.webm")
        traces = _collect_artifacts(PLAYWRIGHT_DIR, "*.zip")

        return _complete_run(
            db, job, run,
            status="done",
            total=total, passed=passed, failed=failed, skipped=skipped,
            duration=duration_sec,
            screenshots=screenshots,
            videos=videos,
            traces=traces,
        )

    except subprocess.TimeoutExpired:
        return _complete_run(
            db, job, run, status="fail",
            total=0, passed=0, failed=0, skipped=0, duration=DEFAULT_TIMEOUT,
            error=f"测试执行超时 ({DEFAULT_TIMEOUT}s)",
        )
    except Exception as e:
        logger.exception(f"Playwright run error for job {job_id}")
        return _complete_run(
            db, job, run, status="fail",
            total=0, passed=0, failed=0, skipped=0, duration=0,
            error=f"执行异常: {type(e).__name__}: {e}",
        )


# ── Helpers ──

def _fail_job(db: Session, job_id: int, message: str) -> dict:
    """标记任务为失败，无需创建运行记录。"""
    from app.models.ui_test import UiTestJob
    job = db.query(UiTestJob).filter(UiTestJob.id == job_id).first()
    if job:
        job.status = "fail"
        job.last_result = json.dumps({"error": message}, ensure_ascii=False)
        db.commit()
    return {"error": message}


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
    """完成一次运行，更新 run 和 job 状态。"""
    result = {
        "total": total, "pass_": passed, "fail": failed,
        "skip": skipped, "duration": duration,
    }
    if error:
        result["error"] = error

    run.result = json.dumps(result, ensure_ascii=False)
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
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
        "started_at": run.started_at, "finished_at": run.finished_at,
    }


def _collect_artifacts(base_dir: Path, pattern: str) -> list[str]:
    """收集产物路径。"""
    items = []
    try:
        for f in base_dir.rglob(pattern):
            items.append(str(f.relative_to(base_dir)).replace("\\", "/"))
    except Exception:
        pass
    return items[:20]  # max 20
