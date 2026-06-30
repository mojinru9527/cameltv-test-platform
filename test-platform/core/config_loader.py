"""配置加载与合并。

v2 解析顺序（推荐，单项目）:
    config/project.yaml
    config/environments/<env>.yaml
    → RunContext

v1 解析顺序（兼容，多站点）:
    platform.yaml
    sites/<site>/site.yaml (extends: _base → _base/apis.yaml + _base/ignore.yaml)
    sites/<site>/environments/<env>.yaml
    → RunContext

特性:
- ${VAR} 环境变量插值（先 load .env）
- 站点对基线接口的 deep-merge 覆盖；值为 null 表示删除该接口
- vpn07_check() prod 环境前置校验，代理不通直接 fail fast
"""
from __future__ import annotations

import os
import re
import socket
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from core.models import (
    ApiDef,
    DepDB,
    DepHTTP,
    DepMQ,
    DepRedis,
    ElkSource,
    EnvConfig,
    FileLogSource,
    LogConfig,
    PlatformConfig,
    PresetData,
    ProjectConfig,
    RunContext,
    SiteConfig,
)

# test-platform/ 根目录（本文件位于 core/）
ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SITES_DIR = CONFIG_DIR / "sites"
ENVIRONMENTS_DIR = CONFIG_DIR / "environments"
PROJECTS_DIR = CONFIG_DIR / "projects"

_VAR_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")
_dotenv_loaded = False
_warned_missing: set[str] = set()   # 已告警过的缺失变量，避免重复刷屏


def _ensure_dotenv() -> None:
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv(ROOT / ".env")
        _dotenv_loaded = True


def _sub_var(m: "re.Match") -> str:
    """替换单个 ${VAR}；变量未定义时替换为空串并告警一次（避免神秘的连接超时）。"""
    name = m.group(1)
    if name in os.environ:
        return os.environ[name]
    if name not in _warned_missing:
        _warned_missing.add(name)
        import sys
        print(f"[WARN] 环境变量 ${{{name}}} 未定义（.env 缺失？），已替换为空字符串。",
              file=sys.stderr)
    return ""


def _interpolate(value: Any) -> Any:
    """递归把字符串中的 ${VAR} 替换为环境变量值。未定义变量替换为空串并告警。"""
    if isinstance(value, str):
        return _VAR_RE.sub(_sub_var, value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    _ensure_dotenv()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _interpolate(raw)


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并。override 的值覆盖 base；值为 None 表示删除该键。"""
    result = dict(base)
    for k, v in override.items():
        if v is None:
            result.pop(k, None)
        elif isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# =========================================================================== #
# v2: 单项目双环境（推荐）
# =========================================================================== #

def load_project(project_name: str = "") -> ProjectConfig:
    """加载项目配置。默认从 config/project.yaml 读取，也支持 config/projects/<name>/project.yaml。"""
    if project_name:
        path = PROJECTS_DIR / project_name / "project.yaml"
    else:
        path = CONFIG_DIR / "project.yaml"
    raw = _load_yaml(path)
    if not raw:
        return ProjectConfig()

    # 解析 apis
    apis_raw = raw.get("apis", {}) or {}
    apis = {name: ApiDef(name=name, **spec) for name, spec in apis_raw.items()}

    # 解析 elk
    elk_raw = raw.get("elk", {}) or {}
    elk = ElkSource(**elk_raw) if elk_raw else ElkSource()

    return ProjectConfig(
        name=raw.get("name", ""),
        description=raw.get("description", ""),
        version=raw.get("version", ""),
        proxy_strategy=raw.get("proxy_strategy", {}),
        locales=raw.get("locales", ["en"]),
        elk=elk,
        apis=apis,
        ignore_paths=raw.get("ignore_paths", []),
        tolerance=raw.get("tolerance", {}),
    )


def load_environment(env: str) -> EnvConfig:
    """加载环境配置 config/environments/<env>.yaml。"""
    path = ENVIRONMENTS_DIR / f"{env}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"环境配置不存在: {path}")
    raw = _load_yaml(path)
    raw.setdefault("name", env)

    # 解析 dbs
    dbs = [DepDB(**d) for d in raw.get("dbs", []) or []]
    # 解析 redis
    redis = [DepRedis(**r) for r in raw.get("redis", []) or []]
    # 解析 mqs
    mqs = [DepMQ(**m) for m in raw.get("mqs", []) or []]
    # 解析 https
    https = [DepHTTP(**h) for h in raw.get("https", []) or []]
    # 解析 preset_data
    preset = [PresetData(**p) for p in raw.get("preset_data", []) or []]
    # 解析 elk
    elk_raw = raw.get("elk", {}) or {}
    elk = ElkSource(**elk_raw) if elk_raw else ElkSource()

    return EnvConfig(
        name=env,
        kind=raw.get("kind", "test"),
        base_url=raw.get("base_url", ""),
        proxy=raw.get("proxy", ""),
        vpn_required=raw.get("vpn_required", False),
        tun_name=raw.get("tun_name", ""),
        proxy_strategy=raw.get("proxy_strategy", ""),
        auth_token=raw.get("auth_token", ""),
        expect_version=raw.get("expect_version", ""),
        verify_tls=raw.get("verify_tls", None),
        dbs=dbs,
        redis=redis,
        mqs=mqs,
        https=https,
        preset_data=preset,
        elk=elk,
    )


def vpn07_check(env_cfg: EnvConfig) -> None:
    """vpn07 代理前置校验：prod 环境需要 vpn07 tun 模式连通，不通直接 fail fast。"""
    if not env_cfg.vpn_required and env_cfg.proxy_strategy != "vpn07":
        return

    tun_addr = os.environ.get("VPN_TUN_ADDR", "")
    proxy_url = env_cfg.proxy or os.environ.get("UPSTREAM_PROXY", "")

    targets = []
    if tun_addr:
        host, _, port = tun_addr.partition(":")
        targets.append((host, int(port) if port else 1080))
    if proxy_url:
        # 从 http://host:port 解析
        try:
            from urllib.parse import urlparse
            p = urlparse(proxy_url)
            if p.hostname:
                targets.append((p.hostname, p.port or 1080))
        except Exception:
            pass

    if not targets:
        # 无检验目标时不做硬阻断，但给出警告
        import sys
        print("[WARN] prod 环境要求 vpn07 代理但未配置 VPN_TUN_ADDR / UPSTREAM_PROXY，"
              "请确保代理已连通。", file=sys.stderr)
        return

    for host, port in targets:
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return  # 连通 → 放行
        except OSError:
            continue

    raise SystemExit(
        f"[FAIL] prod 环境要求 vpn07 代理，但以下地址均不可达: {targets}\n"
        f"请先连接 vpn07（tun 模式 + 全局流量），再执行 prod 命令。"
    )


def build_context_v2(env: str, project_name: str = "") -> RunContext:
    """v2 路径：project + environment → RunContext。"""
    project = load_project(project_name)
    env_cfg = load_environment(env)

    # prod 环境 vpn07 前置校验
    vpn07_check(env_cfg)

    # 合并 project 和 env 的 elk 配置（env 优先）
    if not env_cfg.elk.url and project.elk.url:
        env_cfg.elk = project.elk

    platform = PlatformConfig(
        default_proxy=env_cfg.proxy or "",
        concurrency=8,
    )

    site_cfg = SiteConfig(
        name=project.name or "default",
        description=project.description,
        apis=project.apis,
        ignore_paths=project.ignore_paths,
        tolerance=project.tolerance,
    )

    return RunContext(
        site=project.name,
        env=env,
        platform=platform,
        site_cfg=site_cfg,
        env_cfg=env_cfg,
        project=project,
    )


# =========================================================================== #
# v1: 多站点多环境（兼容旧路径）
# =========================================================================== #

def load_platform() -> PlatformConfig:
    return PlatformConfig(**_load_yaml(CONFIG_DIR / "platform.yaml"))


def load_site(site: str) -> SiteConfig:
    site_dir = SITES_DIR / site
    if not site_dir.exists():
        raise FileNotFoundError(f"站点不存在: {site}（{site_dir}）")

    site_raw = _load_yaml(site_dir / "site.yaml")
    extends = site_raw.get("extends", "_base")

    base_apis: dict[str, Any] = {}
    base_ignore_paths: list[str] = []
    base_tolerance: dict[str, Any] = {}
    if extends:
        base_dir = SITES_DIR / extends
        base_apis = _load_yaml(base_dir / "apis.yaml").get("apis", {}) or {}
        ig = _load_yaml(base_dir / "ignore.yaml")
        base_ignore_paths = ig.get("ignore_paths", []) or []
        base_tolerance = ig.get("tolerance", {}) or {}

    site_apis = site_raw.get("apis", {}) or {}
    merged_apis_raw = _deep_merge(base_apis, site_apis)
    apis = {name: ApiDef(name=name, **spec) for name, spec in merged_apis_raw.items()}

    ignore_paths = base_ignore_paths + (site_raw.get("ignore_paths", []) or [])
    tolerance = _deep_merge(base_tolerance, site_raw.get("tolerance", {}) or {})

    return SiteConfig(
        name=site,
        description=site_raw.get("description", ""),
        extends=extends,
        apis=apis,
        ignore_paths=ignore_paths,
        tolerance=tolerance,
    )


def load_env_v1(site: str, env: str) -> EnvConfig:
    path = SITES_DIR / site / "environments" / f"{env}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"环境不存在: {site}/{env}（{path}）")
    raw = _load_yaml(path)
    raw.setdefault("name", env)

    dbs = [DepDB(**d) for d in raw.get("dbs", []) or []]
    redis = [DepRedis(**r) for r in raw.get("redis", []) or []]
    mqs = [DepMQ(**m) for m in raw.get("mqs", []) or []]
    https = [DepHTTP(**h) for h in raw.get("https", []) or []]
    preset = [PresetData(**p) for p in raw.get("preset_data", []) or []]

    return EnvConfig(
        name=env,
        kind=raw.get("kind", "test"),
        base_url=raw.get("base_url", ""),
        proxy=raw.get("proxy", ""),
        auth_token=raw.get("auth_token", ""),
        expect_version=raw.get("expect_version", ""),
        dbs=dbs,
        redis=redis,
        mqs=mqs,
        https=https,
        preset_data=preset,
    )


def build_context(site: str, env: str) -> RunContext:
    """v1 路径（兼容）：platform ⊕ site(⊕_base) ⊕ env → RunContext。"""
    return RunContext(
        site=site,
        env=env,
        platform=load_platform(),
        site_cfg=load_site(site),
        env_cfg=load_env_v1(site, env),
    )


# =========================================================================== #
# 日志配置（独立于 RunContext，按需加载）
# =========================================================================== #

def load_log_config(site: str = "") -> LogConfig:
    """加载日志源配置。v2 从 environments 读取 elk；v1 从 sites/<site>/logs.yaml 读取。"""
    # v2: 优先从 project elk 读取
    project = load_project()
    if project.elk and project.elk.url:
        return LogConfig(mode="elk", elk=project.elk)

    # v1: 从 sites/<site>/logs.yaml
    if site:
        path = SITES_DIR / site / "logs.yaml"
        raw = _load_yaml(path)
        if raw:
            files = [FileLogSource(**f) for f in raw.get("files", []) or []]
            elk_raw = raw.get("elk", {}) or {}
            elk = ElkSource(**elk_raw) if elk_raw else ElkSource()
            return LogConfig(mode=raw.get("mode", "files"), files=files, elk=elk)

    return LogConfig()


# =========================================================================== #
# 枚举
# =========================================================================== #

def list_sites() -> list[str]:
    if not SITES_DIR.exists():
        return []
    return sorted(
        d.name
        for d in SITES_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "site.yaml").exists()
    )


def list_envs(site: str) -> list[str]:
    env_dir = SITES_DIR / site / "environments"
    if not env_dir.exists():
        return []
    return sorted(p.stem for p in env_dir.glob("*.yaml"))


def list_environments_v2() -> list[str]:
    """列出 v2 所有可用环境名（test / prod）。"""
    if not ENVIRONMENTS_DIR.exists():
        return []
    return sorted(p.stem for p in ENVIRONMENTS_DIR.glob("*.yaml"))
