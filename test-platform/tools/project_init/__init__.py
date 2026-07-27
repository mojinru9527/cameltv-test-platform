"""项目接入向导：tp init-project <name>

交互式问答 → 生成完整项目骨架：
  config/project.yaml
  config/environments/test.yaml
  config/environments/prod.yaml
  tests/ (目录骨架)
  .env.example
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core import logging as log


def run_init(name: str, out_dir: str = ".") -> None:
    """主入口：交互式初始化新测试项目。"""
    root = Path(out_dir).resolve()
    project_dir = root / name

    if project_dir.exists():
        log.err(f"目录已存在: {project_dir}")
        raise SystemExit(1)

    log.rule(f"项目接入向导 · {name}")
    log.info("按提示填写项目信息，回车使用默认值。\n")

    # --- 基本信息 ---
    description = input("  项目描述 [My Test Project]: ") or "My Test Project"
    version = input("  初始版本 [1.0]: ") or "1.0"

    # --- 测试环境 ---
    log.info("\n--- 测试环境 ---")
    test_url = input("  base_url [https://test.example.com]: ") or "https://test.example.com"
    test_proxy = input("  proxy（内网留空）[]: ") or ""

    # --- 正式环境 ---
    log.info("\n--- 正式环境 ---")
    prod_url = input("  base_url [https://www.example.com]: ") or "https://www.example.com"
    prod_proxy_needed = input("  是否需要代理? [y/N]: ").lower() == "y"
    prod_proxy = ""
    vpn = False
    tun = ""
    if prod_proxy_needed:
        prod_proxy = input("  proxy 地址 [http://127.0.0.1:7890]: ") or "http://127.0.0.1:7890"
        vpn_name = input("  VPN/TUN 名称（留空无）[]: ") or ""
        if vpn_name:
            vpn = True
            tun = vpn_name

    # --- 数据库 ---
    log.info("\n--- 数据库（留空跳过）---")
    db_name = input("  MySQL/Postgres 逻辑名称 [main]: ") or "main"
    db_type = input("  类型 [mysql]: ") or "mysql"
    db_dsn = input(f"  DSN（含 ${{VAR}} 插值）[]: ") or ""

    # --- ELK ---
    log.info("\n--- ELK 日志（留空跳过）---")
    elk_url = input("  Elasticsearch URL []: ") or ""
    kibana_url = ""
    if elk_url:
        kibana_url = input("  Kibana URL []: ") or ""

    # --- 生成文件 ---
    log.info("\n生成项目骨架...")

    # config/project.yaml
    cfg_dir = project_dir / "config"
    env_dir = cfg_dir / "environments"
    env_dir.mkdir(parents=True, exist_ok=True)

    project_yaml = f"""# {name} — 测试自动化项目配置
name: {name}
description: {description}
version: "{version}"

proxy_strategy:
  test: direct
  prod: {"vpn07" if vpn else "direct"}

locales:
  - en
"""
    if elk_url:
        project_yaml += f"""
elk:
  url: "${{ELASTIC_URL}}"
  kibana_url: "{kibana_url}"
  index: "{name.lower()}-app-*"
  trace_field: "traceId"
  time_field: "@timestamp"
"""
    else:
        project_yaml += "\nelk: {}\n"

    project_yaml += """
apis: {}
ignore_paths: []
tolerance:
  float_abs: 0.01
  array_unordered: true
  ignore_type_str_num: true
"""
    (cfg_dir / "project.yaml").write_text(project_yaml, encoding="utf-8")

    # test.yaml
    test_yaml = _render_env_yaml(name, "test", test_url, test_proxy, False, "", db_name, db_type, db_dsn)
    (env_dir / "test.yaml").write_text(test_yaml, encoding="utf-8")

    # prod.yaml
    prod_yaml = _render_env_yaml(name, "prod", prod_url, prod_proxy, vpn, tun, db_name, db_type, db_dsn)
    (env_dir / "prod.yaml").write_text(prod_yaml, encoding="utf-8")

    # .env.example
    env_example = f"""# {name} — 凭据（复制为 .env 并填写）
UPSTREAM_PROXY={prod_proxy}
VPN_TUN_ADDR=

# --- 测试环境 ---
{name.upper()}_TEST_AUTH_TOKEN=
{name.upper()}_TEST_DB_USER=
{name.upper()}_TEST_DB_PWD=

# --- 正式环境 ---
{name.upper()}_PROD_AUTH_TOKEN=
{name.upper()}_PROD_DB_USER=
{name.upper()}_PROD_DB_PWD=

# --- ELK ---
ELASTIC_URL={elk_url}
ELASTIC_API_KEY=
KIBANA_URL={kibana_url}
"""
    (project_dir / ".env.example").write_text(env_example, encoding="utf-8")

    # tests 骨架
    tests_dir = project_dir / "tests"
    for sub in ["test-cases/functional", "api-testing/collections", "api-testing/generated",
                "automation/ui/tests", "requirements/documents", "requirements/traceability-matrix"]:
        (tests_dir / sub).mkdir(parents=True, exist_ok=True)
        (tests_dir / sub / ".gitkeep").touch()

    log.ok(f"\n项目 '{name}' 初始化完成!")
    log.info(f"位置: {project_dir}")
    log.info("下一步:")
    log.info(f"  1. cd {name}")
    log.info(f"  2. 编辑 config/environments/test.yaml 填入真实连接信息")
    log.info(f"  3. 编辑 config/environments/prod.yaml 填入正式环境信息")
    log.info(f"  4. 复制 .env.example 为 .env 并填写凭据")
    log.info(f"  5. 拉取 swagger: tp api pull --source <swagger-url>")


def _render_env_yaml(name: str, env: str, base_url: str, proxy: str,
                     vpn: bool, tun: str,
                     db_name: str, db_type: str, db_dsn: str) -> str:
    kind = "prod" if env == "prod" else "test"
    vpn_block = ""
    if vpn:
        vpn_block = f"""
vpn_required: true
tun_name: "{tun}"
proxy_strategy: vpn07
"""
    else:
        vpn_block = """
vpn_required: false
proxy_strategy: direct
"""

    db_block = ""
    if db_dsn:
        db_block = f"""
dbs:
  - name: {db_name}
    type: {db_type}
    dsn: "{db_dsn}"
"""

    return f"""# {env.upper()} 环境
name: {env}
kind: {kind}
base_url: "{base_url}"
proxy: "{proxy}"
{vpn_block}
auth_token: "${{{name.upper()}_{env.upper()}_AUTH_TOKEN}}"
expect_version: ""
{db_block}
redis: []
mqs: []
https:
  - name: api-health
    url: "{base_url}/api/health"
preset_data: []
elk:
  index: "*-{env}-*"
  trace_field: "traceId"
  time_field: "@timestamp"
"""
