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
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "ui-runs"
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


def run_playwright_test(db: Session, run_id: int, job_id: int, project_id: int) -> dict:
    """后台执行 Playwright 测试 — 更新已有的 UiTestRun 记录。

    所有代码路径（成功/失败/异常）都会更新 run 状态和 error_message。
    此函数由 BackgroundTasks 调用，使用独立 db session。
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

    # 5. 执行 Playwright
    try:
        npx = _resolve_cmd("npx")
        if not npx:
            return _fail_run(db, run, "npx 命令不可用，请安装 Node.js", job)

        cmd = [
            npx, "playwright", "test", test_spec,
            "--project", browser,
            "--reporter", "json",
            "--output", str(artifact_dir),
        ]
        logger.info(f"Running: {' '.join(cmd)} in {PLAYWRIGHT_DIR}")

        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=DEFAULT_TIMEOUT,
            cwd=str(PLAYWRIGHT_DIR),
            env=env,
        )

        # 5. 解析结果
        stdout_text = result.stdout.strip() if result.stdout else ""
        stderr_text = result.stderr[:2000] if result.stderr else ""

        if result.returncode != 0 and not stdout_text:
            # Playwright 自身错误（非测试失败）
            return _fail_run(
                db, run,
                f"Playwright 执行失败 (exit={result.returncode}): {stderr_text}",
                job,
            )

        # Parse JSON report
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

        # 6. 收集产物（产物目录 + Playwright test-results + Playwright 项目根）
        test_results_dir = PLAYWRIGHT_DIR / "test-results"
        screenshots = (
            _collect_artifacts(artifact_dir, "*.png") +
            _collect_artifacts(test_results_dir, "*.png") +
            _collect_artifacts(PLAYWRIGHT_DIR, "*.png")
        )
        videos = (
            _collect_artifacts(artifact_dir, "*.webm") +
            _collect_artifacts(test_results_dir, "*.webm") +
            _collect_artifacts(PLAYWRIGHT_DIR, "*.webm")
        )
        traces = (
            _collect_artifacts(artifact_dir, "*.zip") +
            _collect_artifacts(test_results_dir, "*.zip") +
            _collect_artifacts(PLAYWRIGHT_DIR, "*.zip")
        )

        # Copy artifacts from test-results and PLAYWRIGHT_DIR into artifact_dir if not already there
        for src_dir in [test_results_dir, PLAYWRIGHT_DIR]:
            if src_dir == artifact_dir or not src_dir.exists():
                continue
            for pattern in ["*.png", "*.webm", "*.zip"]:
                for f in src_dir.rglob(pattern):
                    rel = f.relative_to(src_dir)
                    dest = artifact_dir / rel
                    if not dest.exists():
                        try:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, dest)
                        except Exception:
                            pass

        return _complete_run(
            db, job, run,
            status="done",
            total=total, passed=passed, failed=fail_count, skipped=skipped,
            duration=duration_sec,
            screenshots=screenshots,
            videos=videos,
            traces=traces,
        )

    except subprocess.TimeoutExpired:
        return _fail_run(
            db, run,
            f"测试执行超时 ({DEFAULT_TIMEOUT}s)", job,
        )
    except Exception as e:
        logger.exception(f"Playwright run error for run #{run_id}, job #{job_id}")
        return _fail_run(
            db, run,
            f"执行异常: {type(e).__name__}: {e}", job,
        )


# ── Helpers ──

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
    """收集产物路径。"""
    items = []
    try:
        for f in base_dir.rglob(pattern):
            items.append(str(f.relative_to(base_dir)).replace("\\", "/"))
    except Exception:
        pass
    return items[:20]  # max 20
