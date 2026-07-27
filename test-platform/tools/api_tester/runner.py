"""测试执行器：调 npx playwright test，解析结果，收集 traceId → ELK。

工作流:
  1. 确保 Playwright 及依赖已安装（npx playwright install）
  2. 注入环境变量（baseURL, proxy, auth token, ELK URL）
  3. 执行 npx playwright test
  4. 解析 JSON/JUnit 结果
  5. 失败用例收集 traceId → 调用 log_aggregator 生成 ELK 链接
  6. 输出统一报告
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core import logging as log
from core.models import RunContext

ROOT = Path(__file__).resolve().parent.parent.parent


def _find_npx() -> str:
    """查找 npx 可执行文件（Windows: .cmd, Unix: npx）。

    shutil.which 会扫描当前进程的 PATH；若找不到则尝试 Node.js 默认安装路径。
    """
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx:
        return npx
    # 回退：尝试常见 Node.js 安装路径
    candidates = [
        r"F:\Program Files\nodejs\npx.cmd",
        r"C:\Program Files\nodejs\npx.cmd",
        r"C:\Program Files (x86)\nodejs\npx.cmd",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "npx"  # 最后的回退


class TestRunner:
    """Playwright API 测试执行器。"""

    def __init__(self, ctx: RunContext):
        self.ctx = ctx
        self._results: list[dict[str, Any]] = []

    def run(self, spec_dir: str = "tests/api-testing/generated",
            filter_: str = "", report: str = "",
            base_url_override: str | None = None) -> dict[str, Any]:
        """主入口：执行测试并返回聚合结果。"""
        spec_path = ROOT / spec_dir
        if not spec_path.exists():
            log.err(f"测试目录不存在: {spec_path}")
            raise SystemExit(1)

        # 允许 CLI --base-url 覆盖配置值（本地调试用）
        base_url = base_url_override or self.ctx.base_url

        log.rule(f"API 测试 · {self.ctx.project.name if self.ctx.project else self.ctx.site} · {self.ctx.env}")
        log.info(f"目标: {base_url}")
        log.info(f"测试目录: {spec_path}")

        # 1. 输出报告路径（绝对路径，避免依赖 cwd / Playwright config 相对路径）
        reports_dir = ROOT / "data" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        json_report = reports_dir / f"api-test-{self.ctx.env}-{ts}.json"
        junit_report = Path(report) if report else reports_dir / f"api-test-{self.ctx.env}-{ts}.xml"
        junit_report.parent.mkdir(parents=True, exist_ok=True)

        # 2. 注入环境变量
        env = os.environ.copy()
        env["CAMELTV_BASE_URL"] = base_url
        env["CAMELTV_AUTH_TOKEN"] = self.ctx.env_cfg.auth_token or ""
        if self.ctx.proxy:
            env["HTTP_PROXY"] = self.ctx.proxy
            log.info(f"代理: {self.ctx.proxy}")
        # playwright.config.ts 的 reporter 读取这两个变量，确保报告写到我们指定的绝对路径
        env["JUNIT_OUTPUT"] = str(junit_report)
        env["JSON_OUTPUT"] = str(json_report)

        # 3. 构造命令（Windows 上使用完整路径到 npx.cmd）
        npx = _find_npx()
        cmd = [npx, "playwright", "test"]
        if filter_:
            cmd.extend(["--grep", filter_])
        cmd.append(f"--config={spec_path}/playwright.config.ts")

        # 4. 执行测试
        log.info(f"执行: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=str(spec_path),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,  # 10 分钟超时
            )
        except subprocess.TimeoutExpired:
            log.err("测试执行超时（10 分钟）。")
            return {"total": 0, "passed": 0, "failed": 1, "skipped": 0,
                    "pass_rate": 0, "env": self.ctx.env, "base_url": self.ctx.base_url,
                    "failed_cases": [], "error": "timeout"}

        # 5. 解析结果：优先读我们注入的绝对路径 JSON 报告
        if json_report.exists():
            self._results = self._parse_json_report(json_report)
        else:
            self._results = self._parse_console_output(result.stdout, result.stderr)

        # 7. 收集 traceId 并生成 ELK 链接
        self._enrich_with_elk_links()

        # 8. 输出汇总
        summary = self._summarize(base_url)
        self._print_summary(summary)

        # 9. 返回结果（不在此处 raise；fail fast 由 CLI 层根据 summary['failed'] 决定，
        #    这样 server / 编排层能拿到完整结果 dict）
        return summary

    @staticmethod
    def _walk_suites(suites: list[dict], results: list[dict]) -> None:
        """递归遍历 Playwright JSON reporter 的嵌套 suites/specs/tests 树。

        Playwright v1.60+ 的 JSON reporter 实际结构:
          suites[]                     ← 根（config 级）
            └─ suites[]               ← 文件级（title=文件名, specs=[]）
                 └─ suites[]          ← describe 级（title=分组名）
                      └─ specs[]      ← 测试定义（title=用例名, ok=通过/失败）
                           └─ tests[] ← 测试执行（expectedStatus, results[]）
                                └─ results[] ← 每次重试（status=passed/failed, error）
        """
        for suite in suites:
            # 递归进入嵌套 suites（根 → 文件 → describe 层级）
            nested = suite.get("suites", [])
            if nested:
                TestRunner._walk_suites(nested, results)

            # specs[] 在 describe 层才有内容，文件层 specs=[] 会被跳过
            for spec in suite.get("specs", []):
                spec_title = spec.get("title", "?")
                spec_file = spec.get("file", suite.get("file", ""))

                for test in spec.get("tests", []):
                    retries = test.get("results", [])

                    # 从最后一次重试获取实际结果
                    if retries:
                        last = retries[-1]
                        normalized = last.get("status", "unknown")
                        error_msg = (last.get("error", {}) or {}).get("message", "")
                        duration = last.get("duration", 0)
                    else:
                        # 无重试结果：用 spec.ok 推断
                        normalized = "passed" if spec.get("ok") else "failed"
                        error_msg = ""
                        duration = 0

                    results.append({
                        "name": spec_title,
                        "file": spec_file,
                        "status": normalized,
                        "duration": duration,
                        "error": error_msg,
                        "trace_ids": [],
                        "elk_links": [],
                    })

    def _parse_json_report(self, json_path: Path) -> list[dict[str, Any]]:
        """解析 Playwright JSON reporter 输出。"""
        if not json_path.exists():
            return []
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        results: list[dict[str, Any]] = []
        self._walk_suites(data.get("suites", []), results)
        return results

    def _parse_console_output(self, stdout: str, stderr: str) -> list[dict[str, Any]]:
        """从控制台输出中解析测试结果。"""
        import re
        results = []
        combined = stdout + "\n" + stderr

        # 匹配 Playwright 的输出格式
        pattern = re.compile(
            r"([✓✗])\s+(.+?)\s+\((\d+\.?\d*)(s|ms)\)",
            re.MULTILINE,
        )
        for match in pattern.finditer(combined):
            icon, name, duration, unit = match.groups()
            status = "passed" if icon == "✓" else "failed"
            dur_ms = float(duration) * (1 if unit == "ms" else 1000)
            results.append({
                "name": name.strip(),
                "file": "",
                "status": status,
                "duration": dur_ms,
                "error": "",
                "trace_ids": [],
                "elk_links": [],
            })

        if not results:
            results.append({
                "name": "(控制台解析)",
                "file": "",
                "status": "passed" if "All tests passed" in combined else "failed",
                "duration": 0,
                "error": stderr[:500] if stderr else "",
                "trace_ids": [],
                "elk_links": [],
            })

        return results

    def _enrich_with_elk_links(self) -> None:
        """为失败用例收集 traceId 并生成 ELK 查询链接。"""
        from tools.log_aggregator import get_elk_link, collect_trace_ids_from_text

        for r in self._results:
            if r["status"] != "failed":
                continue

            # 从错误信息中提取 traceId
            trace_ids = collect_trace_ids_from_text(r.get("error", ""))
            r["trace_ids"] = trace_ids

            # 生成 ELK 链接
            for tid in trace_ids:
                link = get_elk_link(self.ctx, tid)
                if link:
                    r["elk_links"].append(link)

    def _summarize(self, base_url: str = "") -> dict[str, Any]:
        """聚合测试结果。"""
        passed = sum(1 for r in self._results if r["status"] == "passed")
        failed = sum(1 for r in self._results if r["status"] == "failed")
        skipped = sum(1 for r in self._results if r["status"] == "skipped")
        total = len(self._results)
        failed_cases = [r for r in self._results if r["status"] == "failed"]

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": (passed / total * 100) if total else 0,
            "env": self.ctx.env,
            "base_url": base_url or self.ctx.base_url,
            "failed_cases": failed_cases,
        }

    def _print_summary(self, summary: dict[str, Any]) -> None:
        """打印测试汇总。"""
        log.rule("API 测试结果")
        log.info(f"环境: {summary['env']} | {summary['base_url']}")
        log.info(f"共 {summary['total']}, 通过 {summary['passed']}, "
                 f"失败 {summary['failed']}, 跳过 {summary['skipped']}")
        log.info(f"通过率: {summary['pass_rate']:.1f}%")

        for case in summary["failed_cases"]:
            log.err(f"  FAIL  {case['name']}")
            for link in case.get("elk_links", []):
                log.info(f"    ELK → {link}")

        if summary["failed"] == 0:
            log.ok("全部通过 ✓")
