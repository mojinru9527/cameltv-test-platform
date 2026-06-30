"""API 测试引擎（Playwright MCP — swagger 优先 + UI 捕获补充）。

用法：
    tp api pull --source <swagger-url>      拉 swagger 生成测试骨架
    tp api run --env test                   运行 Playwright API 测试
    tp api capture --session-id <id>        从 UI 自动化捕获的流量生成测试用例

模块：
    swagger_parser   拉 OpenAPI spec → EndpointSpec 列表
    test_generator   EndpointSpec → TypeScript Playwright 测试文件
    assertion_builder  断言代码生成（status/json/schema/db）
    runner           调 npx playwright test，解析结果，收集 traceId
    dedup            (method, path) 去重，swagger 版优先
    capture_importer  UI 捕获 JSONL → 测试骨架
"""
from __future__ import annotations

from tools.api_tester.swagger_parser import SwaggerParser
from tools.api_tester.test_generator import TestGenerator
from tools.api_tester.runner import TestRunner


def pull_swagger(source_url: str, out_dir: str = "tests/api-testing/generated") -> None:
    """拉取 Swagger/OpenAPI spec 并生成 Playwright 测试骨架。"""
    from core import logging as log

    log.rule(f"API Test · 拉取 Swagger")
    log.info(f"来源: {source_url}")

    parser = SwaggerParser()
    endpoints = parser.parse(source_url)
    log.info(f"解析到 {len(endpoints)} 个接口")

    # 按 tag/服务 分组
    generator = TestGenerator(out_dir)
    count = generator.generate(endpoints, source="swagger")
    log.ok(f"生成 {count} 个 Playwright 测试文件 → {out_dir}")


def run_tests(ctx, spec_dir: str = "tests/api-testing/generated",
              filter_: str = "", report: str = "",
              base_url_override: str | None = None) -> dict:
    """运行 Playwright API 测试，失败自动收集 traceId → ELK。

    返回聚合结果 dict（total/passed/failed/skipped/pass_rate/failed_cases），
    供 server 路由与编排层消费。注意：当存在失败用例时 runner.run() 会抛 SystemExit(2)，
    调用方（CLI）据此 fail fast；server 层捕获 SystemExit 后回报 failed。
    """
    runner = TestRunner(ctx)
    return runner.run(spec_dir=spec_dir, filter_=filter_, report=report,
                      base_url_override=base_url_override)


def import_captured(session_id: str, out_dir: str = "tests/api-testing/captured") -> None:
    """从 UI 自动化捕获的流量生成 API 测试用例。"""
    from core import logging as log
    from tools.api_tester.capture_importer import CaptureImporter
    from tools.api_tester.dedup import Dedup

    log.rule(f"API Test · 导入 UI 捕获流量")
    log.info(f"Session: {session_id}")

    importer = CaptureImporter()
    endpoints = importer.import_session(session_id)
    log.info(f"从流量中提取 {len(endpoints)} 个接口")

    # 与已有 swagger 测试去重
    dedup = Dedup()
    new_endpoints = dedup.deduplicate(endpoints, existing_dir=out_dir)
    log.info(f"去重后新增 {len(new_endpoints)} 个接口（swagger 优先）")

    if new_endpoints:
        generator = TestGenerator(out_dir)
        count = generator.generate(new_endpoints, source="ui-capture")
        log.ok(f"生成 {count} 个补充测试文件 → {out_dir}")
    else:
        log.ok("无新增接口，全部已被 swagger 覆盖。")
