"""统一命令行入口：tp <cmd> --env <环境> ...

Batch 98：V1 工具命令（capture/apidiff/mock/envcheck/datafactory/logagg/report/api/init-project）
已随 11 个工具目录废弃删除，CLI 仅保留 config 自检命令；web-ui/server/cli 整体退役决策见 Batch 99 覆盖矩阵。
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
    """自动选择 v2 或 v1 路径构建 RunContext。"""
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
    project = cl.load_project()
    if project.name:
        envs = cl.list_environments_v2()
        click.echo(f"[v2] {project.name} (v{project.version}): {', '.join(envs)}")

    for s in cl.list_sites():
        click.echo(f"[v1] {s}: {', '.join(cl.list_envs(s)) or '(无环境)'}")


if __name__ == "__main__":
    main()
