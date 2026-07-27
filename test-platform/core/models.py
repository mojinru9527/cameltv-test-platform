"""配置数据模型（pydantic v2）。

两层加载路径：
  v2（推荐）：project.yaml ⊕ environments/<env>.yaml → RunContext（单项目双环境）
  v1（兼容）：platform.yaml ⊕ sites/<site>/site.yaml ⊕ environments/<env>.yaml → RunContext（多站点）
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# API 定义
# --------------------------------------------------------------------------- #
class ApiDef(BaseModel):
    """单个接口定义。共享基线放 _base/apis.yaml，站点差异在 site.yaml 覆盖。"""
    name: str
    path: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    description: str = ""
    query: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    expect_status: int = 200
    expect_fields: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# 环境依赖
# --------------------------------------------------------------------------- #
class DepDB(BaseModel):
    name: str
    type: Literal["mysql", "postgres"] = "mysql"
    dsn: str
    check: Literal["ping", "rw"] = "ping"


class DepRedis(BaseModel):
    name: str = "redis"
    host: str
    port: int = 6379
    password: str = ""
    db: int = 0


class DepMQ(BaseModel):
    name: str
    type: Literal["rabbitmq", "kafka"] = "rabbitmq"
    url: str


class DepHTTP(BaseModel):
    name: str
    url: str
    expect_version: str = ""


class PresetData(BaseModel):
    db: str
    table: str
    min_rows: int = 1
    where: str = ""


# --------------------------------------------------------------------------- #
# 日志源（ELK / files）
# --------------------------------------------------------------------------- #
class ElkSource(BaseModel):
    url: str = ""
    api_key: str = ""
    kibana_url: str = ""
    index: str = "*"
    trace_field: str = "traceId"
    time_field: str = "@timestamp"


class FileLogSource(BaseModel):
    service: str
    path: str


class LogConfig(BaseModel):
    mode: Literal["files", "elk"] = "files"
    files: list[FileLogSource] = Field(default_factory=list)
    elk: ElkSource = Field(default_factory=ElkSource)


# --------------------------------------------------------------------------- #
# 项目配置（v2 单项目模型）
# --------------------------------------------------------------------------- #
class ProjectConfig(BaseModel):
    """单项目元信息 — 对应 config/project.yaml。"""
    name: str = ""
    description: str = ""
    version: str = ""                   # 当前迭代版本，如 "14.0"
    proxy_strategy: dict[str, str] = Field(default_factory=dict)  # {"test":"direct","prod":"vpn07"}
    locales: list[str] = Field(default_factory=lambda: ["en"])
    elk: ElkSource = Field(default_factory=ElkSource)
    # 接口目录（等同于旧 _base/apis.yaml）
    apis: dict[str, ApiDef] = Field(default_factory=dict)
    ignore_paths: list[str] = Field(default_factory=list)
    tolerance: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 环境 / 站点（v1 兼容）
# --------------------------------------------------------------------------- #
class EnvConfig(BaseModel):
    """单环境连接配置（test / prod）。"""
    name: str
    kind: Literal["prod", "test"] = "test"
    base_url: str
    proxy: str = ""
    # v2 新增
    vpn_required: bool = False
    tun_name: str = ""                  # vpn07
    proxy_strategy: Literal["direct", "vpn07", ""] = ""
    # 凭据
    auth_token: str = ""
    expect_version: str = ""
    # TLS 校验：None=按 kind 推断（prod 校验、test 不校验），显式 true/false 可覆盖
    verify_tls: bool | None = None
    # 依赖
    dbs: list[DepDB] = Field(default_factory=list)
    redis: list[DepRedis] = Field(default_factory=list)
    mqs: list[DepMQ] = Field(default_factory=list)
    https: list[DepHTTP] = Field(default_factory=list)
    preset_data: list[PresetData] = Field(default_factory=list)
    # 日志
    elk: ElkSource = Field(default_factory=ElkSource)


class SiteConfig(BaseModel):
    """站点配置（v1 兼容）。"""
    name: str = ""              # 默认值，使 RunContext.site_cfg 的 default_factory 可用
    description: str = ""
    extends: str = "_base"
    apis: dict[str, ApiDef] = Field(default_factory=dict)
    ignore_paths: list[str] = Field(default_factory=list)
    tolerance: dict[str, Any] = Field(default_factory=dict)


class PlatformConfig(BaseModel):
    """全局配置。"""
    default_proxy: str = ""
    concurrency: int = 8
    recordings_dir: str = "data/recordings"
    reports_dir: str = "data/reports"
    stubs_dir: str = "data/stubs"
    db_path: str = "data/platform.sqlite"


# --------------------------------------------------------------------------- #
# 运行上下文
# --------------------------------------------------------------------------- #
class RunContext(BaseModel):
    site: str = ""
    env: str
    platform: PlatformConfig = Field(default_factory=PlatformConfig)
    site_cfg: SiteConfig = Field(default_factory=SiteConfig)       # v1 兼容
    env_cfg: EnvConfig
    # v2
    project: ProjectConfig | None = None

    @property
    def base_url(self) -> str:
        return self.env_cfg.base_url.rstrip("/")

    @property
    def proxy(self) -> str:
        return self.env_cfg.proxy or self.platform.default_proxy

    @property
    def verify_tls(self) -> bool:
        """TLS 校验策略：显式配置优先，否则 prod 校验、test 不校验。"""
        if self.env_cfg.verify_tls is not None:
            return self.env_cfg.verify_tls
        return self.env_cfg.kind == "prod"

    @property
    def apis(self) -> dict[str, ApiDef]:
        # v2 优先
        if self.project and self.project.apis:
            return self.project.apis
        return self.site_cfg.apis

    def api(self, name: str) -> ApiDef:
        apis = self.apis
        if name not in apis:
            raise KeyError(f"未定义接口 '{name}'")
        return apis[name]
