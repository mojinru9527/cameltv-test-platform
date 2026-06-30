"""测试报告聚合器：解析多框架报告（junit/pytest/jest/Playwright JSON）→ sqlite → 趋势看板。

支持的输入格式:
  - JUnit XML (pytest / jest / TestNG)
  - Playwright JSON reporter 输出

数据库:
  runs(id, build, branch, site, source, ts, total, passed, failed, skipped, duration)
  cases(run_id, name, classname, status, time, trace_id)

source 字段: functional | api | ui
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core import logging as log
from core.config_loader import ROOT, load_platform

HERE = Path(__file__).resolve().parent


def _db_path() -> Path:
    p = ROOT / load_platform().db_path
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      build TEXT, branch TEXT, site TEXT, source TEXT DEFAULT 'api', ts TEXT,
      total INT, passed INT, failed INT, skipped INT, duration REAL);
    CREATE TABLE IF NOT EXISTS cases(
      run_id INT, name TEXT, classname TEXT, status TEXT, time REAL, trace_id TEXT);
    """)


def ingest(files: list[str], build: str = "local", branch: str = "main",
           site: str = "", source: str = "api") -> None:
    """解析多框架报告入库。自动检测格式（JUnit XML / Playwright JSON）。"""
    conn = sqlite3.connect(_db_path())
    _init_db(conn)

    all_cases: list[tuple] = []
    total = passed = failed = skipped = 0
    duration = 0.0

    for fp in files:
        path = Path(fp)
        if not path.exists():
            log.warn(f"报告文件不存在: {fp}")
            continue

        if path.suffix == ".json":
            cases, counts = _parse_playwright_json(path)
        else:
            cases, counts = _parse_junit_xml(path)

        all_cases.extend(cases)
        total += counts["total"]
        passed += counts["passed"]
        failed += counts["failed"]
        skipped += counts["skipped"]
        duration += counts["duration"]

    if not all_cases:
        log.warn("未解析到任何测试用例。")
        conn.close()
        return

    ts = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO runs(build,branch,site,source,ts,total,passed,failed,skipped,duration) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (build, branch, site, source, ts, total, passed, failed, skipped, round(duration, 2)),
    )
    run_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO cases(run_id,name,classname,status,time,trace_id) VALUES (?,?,?,?,?,?)",
        [(run_id, c[0], c[1], c[2], c[3], c[4] if len(c) > 4 else "") for c in all_cases],
    )
    conn.commit()

    # 导出 summary JSON 供 Web UI 消费
    _export_summary(run_id, build, branch, source, site, total, passed, failed, skipped, duration)

    conn.close()
    rate = (passed / total * 100) if total else 0
    log.ok(f"入库 build={build} [{source}]: 共 {total}, 通过 {passed}（{rate:.1f}%）, 失败 {failed}, 跳过 {skipped}")


def _parse_junit_xml(path: Path) -> tuple[list[tuple], dict[str, Any]]:
    """解析 JUnit XML 格式报告。"""
    from junitparser import JUnitXml
    cases: list[tuple] = []
    total = passed = failed = skipped = 0
    duration = 0.0

    xml = JUnitXml.fromfile(str(path))
    for suite in xml:
        for case in suite:
            total += 1
            duration += case.time or 0.0
            results = getattr(case, "result", []) or []
            kinds = {r.__class__.__name__ for r in results}
            if "Failure" in kinds or "Error" in kinds:
                status = "failed"; failed += 1
            elif "Skipped" in kinds:
                status = "skipped"; skipped += 1
            else:
                status = "passed"; passed += 1

            # 提取 trace_id
            trace_id = ""
            error_text = ""
            for r in results:
                error_text += f"{getattr(r, 'message', '')} {getattr(r, 'text', '')}"
            if error_text:
                import re
                m = re.search(r"trace[_-]?id[=:\s\"]+([a-zA-Z0-9\-]+)", error_text, re.IGNORECASE)
                if m:
                    trace_id = m.group(1)

            cases.append((case.name, case.classname or "", status, case.time or 0.0, trace_id))

    return cases, {"total": total, "passed": passed, "failed": failed, "skipped": skipped, "duration": duration}


def _parse_playwright_json(path: Path) -> tuple[list[tuple], dict[str, Any]]:
    """解析 Playwright JSON reporter 输出。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0.0}

    cases: list[tuple] = []
    total = passed = failed = skipped = 0
    duration = 0.0

    for suite in data.get("suites", []):
        classname = suite.get("title", "")
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                total += 1
                status = test.get("status", "skipped")
                dur = test.get("duration", 0)
                duration += dur

                if status == "passed":
                    passed += 1
                elif status in ("failed", "timedOut"):
                    failed += 1
                else:
                    skipped += 1

                # 提取 trace_id
                import re
                trace_id = ""
                error = test.get("error", {})
                error_text = error.get("message", "") if isinstance(error, dict) else str(error)
                m = re.search(r"trace[_-]?id[=:\s\"]+([a-zA-Z0-9\-]+)", error_text, re.IGNORECASE)
                if m:
                    trace_id = m.group(1)

                cases.append((test.get("title", "?"), classname, status, dur, trace_id))

    return cases, {"total": total, "passed": passed, "failed": failed, "skipped": skipped, "duration": duration}


def _export_summary(run_id: int, build: str, branch: str, source: str,
                    site: str, total: int, passed: int, failed: int, skipped: int,
                    duration: float) -> None:
    """导出 summary JSON 给 Web UI 消费。"""
    summary_dir = ROOT / "data" / "reports" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "run_id": run_id,
        "build": build,
        "branch": branch,
        "source": source,
        "site": site,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round((passed / total * 100), 1) if total else 0,
        "duration": round(duration, 2),
    }

    out_path = summary_dir / f"run-{run_id}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def serve(port: int = 8090) -> None:
    app = HERE / "dashboard.py"
    log.rule("测试报告看板")
    log.info(f"打开 http://localhost:{port}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app),
         "--server.port", str(port), "--server.headless", "true"],
        check=False,
    )
