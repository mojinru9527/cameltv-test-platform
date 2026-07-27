"""统一命令行入口：tp <工具> --env <环境> ...

v2（推荐）：tp <cmd> --env test|prod                  ← 单项目双环境
v1（兼容）：tp <cmd> --site <站点> --env <环境>        ← 多站点

设计：所有工具共享 --env，由 core.config_loader 合并出 RunContext。
工具实现按需惰性导入，便于增量交付与降低启动开销。
"""
from __future__ import annotations

import json

import click

from core import config_loader as cl
from core import logging as log


# 公共选项装饰器 ------------------------------------------------------------- #
def site_option(f, required: bool = False):
    return click.option("--site", required=required, default="", help="站点名（v1 兼容）。v2 留空即可。")(f)


def env_option(f, required: bool = True):
    return click.option("--env", required=required, default="test", help="环境名：test | prod")(f)


def _resolve_context(site: str, env: str):
    """自动选择 v2 或 v1 路径构建 RunContext。
    v2: site 为空时走 project + environments/<env>
    v1: site 非空时走到 sites/<site>/environments/<env>
    """
    if site:
        return cl.build_context(site, env)
    return cl.build_context_v2(env)


@click.group()
@click.version_option("0.2.0", prog_name="tp")
def main() -> None:
    """CamelTv 测试自动化平台 — 可移植的测试平台 CLI。"""


# =========================================================================== #
# config —— 配置自检
# =========================================================================== #
@main.group()
def config() -> None:
    """配置查看与校验。"""


@config.command("show")
@site_option
@env_option
def config_show(site: str, env: str) -> None:
    """打印合并后的 RunContext（v2: project ⊕ env，v1: platform ⊕ site ⊕ env）。"""
    ctx = _resolve_context(site, env)
    log.rule(f"{ctx.project.name if ctx.project else ctx.site} / {ctx.env}")

    out: dict = {
        "project": ctx.project.name if ctx.project else "(none)",
        "site": ctx.site or "(v2 mode)",
        "env": ctx.env,
        "base_url": ctx.base_url,
        "proxy": ctx.proxy or "(none)",
        "proxy_strategy": ctx.env_cfg.proxy_strategy or "direct",
        "vpn_required": ctx.env_cfg.vpn_required,
        "expect_version": ctx.env_cfg.expect_version,
        "api_count": len(ctx.apis),
        "apis": sorted(ctx.apis.keys())[:20],
        "deps": {
            "dbs": [d.name for d in ctx.env_cfg.dbs],
            "redis": [r.name for r in ctx.env_cfg.redis],
            "mqs": [m.name for m in ctx.env_cfg.mqs],
            "https": [h.name for h in ctx.env_cfg.https],
        },
        "ignore_paths": (
            ctx.project.ignore_paths if ctx.project else ctx.site_cfg.ignore_paths
        ),
    }
    click.echo(json.dumps(out, ensure_ascii=False, indent=2))


@config.command("sites")
def config_sites() -> None:
    """列出全部站点（v1）+ v2 项目。"""
    # v2 项目
    project = cl.load_project()
    if project.name:
        envs = cl.list_environments_v2()
        click.echo(f"[v2] {project.name} (v{project.version}): {', '.join(envs)}")

    # v1 站点
    for s in cl.list_sites():
        click.echo(f"[v1] {s}: {', '.join(cl.list_envs(s)) or '(无环境)'}")


# =========================================================================== #
# capture —— 流量监控器（mitmproxy 录制）
# =========================================================================== #
@main.command("capture")
@site_option
@env_option
@click.option("--port", default=8081, show_default=True, help="mitmproxy 监听端口")
@click.option("--out", default="", help="录制输出文件，默认 data/recordings/<env>.json")
def capture(site: str, env: str, port: int, out: str) -> None:
    """启动 mitmproxy 抓取站点真实请求并落盘。"""
    from tools.traffic_monitor import run_capture
    ctx = _resolve_context(site, env)
    run_capture(ctx, port=port, out=out)


# =========================================================================== #
# apidiff —— 双环境回放比对
# =========================================================================== #
@main.command("apidiff")
@click.option("--site", default="", help="站点名（v1 兼容）")
@click.option("--base", "base_env", required=True, help="基线环境，如 prod")
@click.option("--target", "target_env", required=True, help="目标环境，如 test")
@click.option("--cases", required=True, help="请求集：录制 JSON 或 cases.yaml")
@click.option("--report", default="", help="HTML 报告路径")
def apidiff(site: str, base_env: str, target_env: str, cases: str, report: str) -> None:
    """同一批请求打两个环境，JSON 逐字段比对并分级出 HTML 报告。"""
    from tools.api_diff import run_diff
    run_diff(site, base_env, target_env, cases, report)


# =========================================================================== #
# mock —— WireMock 编排
# =========================================================================== #
@main.group()
def mock() -> None:
    """Mock Server（容器化 WireMock）。"""


@mock.command("up")
@click.option("--site", default="", help="站点名（v1 兼容）")
@click.option("--port", default=8080, show_default=True)
def mock_up(site: str, port: int) -> None:
    """启动 WireMock 容器并加载该站点的 stub。"""
    from tools.mock_server import up
    up(site, port=port)


@mock.command("down")
def mock_down() -> None:
    """停止 WireMock 容器。"""
    from tools.mock_server import down
    down()


@mock.command("convert")
@click.option("--site", default="", help="站点名（v1 兼容）")
@click.option("--recording", required=True, help="mitmproxy 录制 JSON")
def mock_convert(site: str, recording: str) -> None:
    """把录制流量转换为 WireMock stub 映射。"""
    from tools.mock_server import convert
    convert(site, recording)


@mock.command("inject")
@click.option("--path", required=True, help="目标接口路径，如 /api/pay/order")
@click.option("--status", type=int, default=500, show_default=True)
@click.option("--scenario", default="", help="场景名，如 timeout（与 status 二选一）")
@click.option("--port", default=8080, show_default=True)
def mock_inject(path: str, status: int, scenario: str, port: int) -> None:
    """对指定接口注入故障（500 / 超时等）。"""
    from tools.mock_server import inject
    inject(path, status=status, scenario=scenario, port=port)


# =========================================================================== #
# envcheck —— 环境健康检查
# =========================================================================== #
@main.command("envcheck")
@site_option
@env_option
def envcheck(site: str, env: str) -> None:
    """并发探活依赖（DB/Redis/MQ/HTTP/版本/预置数据），输出红绿灯。"""
    from tools.env_check import run_check
    ctx = _resolve_context(site, env)
    if not run_check(ctx):
        raise SystemExit(1)


# =========================================================================== #
# datafactory —— 测试数据工厂
# =========================================================================== #
@main.command("datafactory")
@site_option
@env_option
@click.option("--rule", required=True, help="数据规则 YAML")
@click.option("--count", default=10, show_default=True)
@click.option("--mode", type=click.Choice(["normal", "dirty"]), default="normal")
@click.option("--template", default="", help="预存场景模板名，如 vip_user")
@click.option("--output", type=click.Choice(["db", "sql", "json"]), default="db")
def datafactory(site, env, rule, count, mode, template, output) -> None:
    """按规则生成成套数据并灌库 / 导出。"""
    from tools.data_factory import run_gen
    ctx = _resolve_context(site, env)
    run_gen(ctx, rule=rule, count=count, mode=mode, template=template, output=output)


# =========================================================================== #
# logagg —— 日志聚合
# =========================================================================== #
@main.group()
def logagg() -> None:
    """日志聚合分析（按 traceId 串全链路）。"""


@logagg.command("trace")
@site_option
@env_option
@click.option("--id", "trace_id", required=True, help="traceId")
@click.option("--out", default="", help="HTML 输出，默认 data/reports/trace-<id>.html")
def logagg_trace(site, env, trace_id, out) -> None:
    """按 traceId 拉全链路日志并高亮 ERROR。"""
    from tools.log_aggregator import trace
    ctx = _resolve_context(site, env)
    trace(ctx, trace_id, out)


@logagg.command("batch")
@site_option
@env_option
@click.option("--report", required=True, help="测试结果 XML（junit）")
@click.option("--cluster/--no-cluster", default=True)
def logagg_batch(site, env, report, cluster) -> None:
    """批量按失败用例 traceId 聚类相同根因。"""
    from tools.log_aggregator import batch
    ctx = _resolve_context(site, env)
    batch(ctx, report, cluster)


# =========================================================================== #
# report —— 报告聚合看板
# =========================================================================== #
@main.group()
def report() -> None:
    """测试报告聚合与趋势看板。"""


@report.command("ingest")
@click.option("--file", "files", multiple=True, required=True, help="报告文件（可多次）")
@click.option("--build", default="local", help="构建号")
@click.option("--branch", default="main")
@click.option("--site", default="", help="可选：标注站点")
@click.option("--source", "source", default="api", help="报告来源: functional|api|ui")
def report_ingest(files, build, branch, site, source) -> None:
    """解析多框架报告入库。"""
    from tools.report_dashboard import ingest
    ingest(list(files), build=build, branch=branch, site=site, source=source)


@report.command("serve")
@click.option("--port", default=8090, show_default=True)
def report_serve(port: int) -> None:
    """启动 streamlit 趋势看板。"""
    from tools.report_dashboard import serve
    serve(port=port)


# =========================================================================== #
# api —— API 测试（Playwright MCP）
# =========================================================================== #
@main.group()
def api() -> None:
    """API 测试（Playwright MCP — swagger 优先 + UI 捕获补充）。"""


@api.command("pull")
@click.option("--source", "source_url", required=True, help="Swagger/OpenAPI URL 或本地路径")
@click.option("--out", "out_dir", default="tests/api-testing/generated", help="输出目录")
def api_pull(source_url: str, out_dir: str) -> None:
    """拉取 Swagger/OpenAPI spec 并生成 Playwright 测试骨架。"""
    from tools.api_tester import pull_swagger
    pull_swagger(source_url, out_dir)


@api.command("run")
@env_option
@click.option("--spec", default="tests/api-testing/generated", help="测试文件目录")
@click.option("--filter", "filter_", default="", help="过滤 smoke | regression")
@click.option("--report", default="", help="JUnit 报告输出路径")
@click.option("--base-url", default="", help="覆盖配置中的 base_url（本地调试用）")
def api_run(env: str, spec: str, filter_: str, report: str, base_url: str) -> None:
    """运行 Playwright API 测试。失败自动收集 traceId → ELK。"""
    from tools.api_tester import run_tests
    ctx = cl.build_context_v2(env)
    summary = run_tests(ctx, spec_dir=spec, filter_=filter_, report=report,
                        base_url_override=base_url or None)
    # fail fast：有失败用例 → 非 0 退出码，便于卡 CI
    if summary.get("failed", 0) > 0:
        raise SystemExit(2)


@api.command("capture")
@click.option("--session-id", required=True, help="UI 自动化 session ID")
@click.option("--out", default="tests/api-testing/captured", help="输出目录")
def api_capture(session_id: str, out: str) -> None:
    """从 UI 自动化捕获的流量生成 API 测试用例（source: ui-capture）。"""
    from tools.api_tester import import_captured
    import_captured(session_id, out_dir=out)


# =========================================================================== #
# init-project —— 项目接入向导
# =========================================================================== #
@main.command("init-project")
@click.argument("name")
@click.option("--out", default=".", help="输出根目录")
def init_project(name: str, out: str) -> None:
    """初始化新测试项目骨架（交互式问答）。"""
    from tools.project_init import run_init
    run_init(name, out_dir=out)


if __name__ == "__main__":
    main()
