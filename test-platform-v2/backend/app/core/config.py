"""Application settings loaded from environment variables.

Security: ALL sensitive values (secret_key, passwords, API keys) MUST be
provided via environment variables or .env file in production.
Default empty values will cause a startup validation error in production mode.
"""
from __future__ import annotations

import os
import secrets
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App identity ──
    app_name: str = "CamelTv Test Platform API"
    app_version: str = "2.1.0"
    environment: str = "development"          # "development" | "production"

    # ── Security (sensitive — no hardcoded defaults) ──
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ── Auth cookie (P1-1: JWT via httpOnly cookie, XSS-hardened) ──
    cookie_name: str = "cameltv_token"
    cookie_secure: bool = False               # production: true (requires HTTPS)
    cookie_samesite: str = "lax"              # "strict" | "lax" | "none"
    cookie_domain: str = ""                    # empty = host-only cookie
    cookie_path: str = "/api"

    # ── CSRF protection (P1-1/S1d) ──
    csrf_enabled: bool = True
    csrf_allowed_origins: str = ""             # comma-separated; empty = use allowed_origins

    # ── CSP (P1-2/S2c) ──
    csp_enabled: bool = True
    csp_header: str = "script-src 'self' cdn.jsdelivr.net; object-src 'none'; base-uri 'self'"

    # ── Security headers (C3) ──
    security_headers_enabled: bool = True

    # ── Database ──
    database_url: str = "sqlite:///./data/platform.db"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_create_tables: bool = True

    # ── PostgreSQL connection pooling (V2.6) ──
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Default admin ──
    admin_username: str = "admin"
    admin_password: str = ""                   # production: required; dev auto-generates

    # ── Seed users ──
    tester_password: str = ""                  # empty = auto-generate in dev; required in prod
    tester_username: str = "tester"

    # ── ELK ──
    elk_base_url: str = ""
    elk_index: str = "*"

    # ── AI / LLM ──
    ai_enabled: bool = True
    ai_api_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""                       # production: required
    ai_model: str = "deepseek-chat"
    ai_max_tokens: int = 16384                 # each sub-call gets full budget (model caps at 8K, but split strategy doubles effective output)
    ai_temperature: float = 0.3
    ai_split_calls: bool = True                # split generation into functional + API parallel calls to avoid truncation

    # ── AI 降级 / 超时（DeepSeek 分类器不可用时的本地降级提取）──
    ai_timeout_seconds: float = 180.0          # 单次 AI 调用超时（秒）
    ai_retry_attempts: int = 2                 # 瞬时失败（超时/网络）总尝试次数，最小 1
    ai_fallback_on_failure: bool = True        # 瞬时失败时降级到本地模块提取，返回可复核草稿而非硬失败

    # ── File paths (configurable for portability) ──
    workspace_root: str = ""      # empty = auto-detect from app/services/__file__
    skill_dir: str = ""           # test-case-design skill directory
    lanhu_mcp_dir: str = ""       # lanhu-mcp module directory
    data_dir: str = ""            # extracted data cache directory

    # ── SMTP (optional, for email notifications) ──
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_verify_cert: bool = True       # P1-S5b: SMTP TLS 证书验证开关
    smtp_ca_bundle: str = ""             # P1-S5b: 自定义 CA 证书包路径

    # ── External Integration Sync (V2.6) ──
    sync_enabled: bool = True
    sync_retry_attempts: int = 2
    sync_timeout_seconds: int = 30

    # ── Knowledge Center / RAG / Agent (M0 治理开关) ──
    # 安全默认：全部 OFF。知识入库为写路径的后台副作用，须由运维在评审脱敏与容量后
    # 显式开启（避免合入即在共享/测试环境自动激活对全量写操作的入库）。
    knowledge_ingest_enabled: bool = False       # M1 知识源入库总开关（默认关，显式开启）
    rag_enabled: bool = False                    # 是否启用 RAG 检索（M2）
    knowledge_graph_enabled: bool = False        # 是否启用知识图谱（M3）
    ai_artifact_allow_batch_import: bool = False # AI 产物是否允许批量导入正式库
    knowledge_ingest_production_data: bool = False  # 生产环境执行结果是否允许进入知识库

    # ── M2 向量化 / 混合检索（RAG）──
    # 本地 fastembed(onnx) 嵌入，离线不外传（见 ADR-0010）。仅在 rag_enabled 时激活嵌入管线。
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # 中文小模型，512 维
    embedding_dim: int = 512
    embedding_batch_size: int = 32               # 批量嵌入/回填批大小
    embedding_cache_dir: str = ""                # 空=fastembed 默认（~/.cache/fastembed）
    # bge 检索建议对 query 加前缀以对齐训练目标；passage 侧不加
    embedding_query_prefix: str = "为这个句子生成表示以用于检索相关文章："

    # ── LLM-Wiki 知识库 / 差异对比（VNext-1..3 治理开关）──
    # 安全默认全部 OFF：Wiki 编译与差异对比会调用 LLM（成本），须由运维显式开启。
    # external_llm_wiki_enabled 留待 VNext-5 外部连接器。
    wiki_enabled: bool = False                   # 平台内 Wiki 知识库总开关（导入/编译/页面）
    wiki_auto_ingest_enabled: bool = False       # 导入 raw source 后是否自动触发 Wiki 编译
    wiki_diff_enabled: bool = False              # 是否启用知识库差异对比
    wiki_auto_create_artifact: bool = False      # 差异是否自动生成待审 AI 产物
    lanhu_mcp_enabled: bool = True               # 是否启用蓝湖 MCP 提取

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @cached_property
    def effective_admin_password(self) -> str:
        """Dev: auto-generate a random password when unconfigured (logged to console)."""
        if self.admin_password:
            return self.admin_password
        if self.environment == "development":
            pwd = secrets.token_urlsafe(12)
            import logging
            logging.getLogger("uvicorn").warning(
                "[security] ADMIN_PASSWORD not set — auto-generated dev password: %s (valid this session only)",
                pwd,
            )
            return pwd
        return ""  # production will fail validation

    @cached_property
    def effective_secret_key(self) -> str:
        """Dev: auto-generate a random key when unconfigured (logged to console)."""
        if self.secret_key:
            return self.secret_key
        if self.environment == "development":
            key = secrets.token_hex(32)
            import logging
            logging.getLogger("uvicorn").warning(
                "[security] SECRET_KEY not set — auto-generated dev key (valid this session only)"
            )
            return key
        return ""

    def validate_security(self) -> list[str]:
        """Return a list of security misconfigurations; empty list = ok."""
        issues: list[str] = []

        if self.environment == "production":
            if not self.secret_key or self.secret_key.startswith("dev-"):
                issues.append("SECRET_KEY 未设置或仍为开发默认值，请通过环境变量/secret 管理设置强密钥")
            if not self.admin_password or self.admin_password == "admin123":
                issues.append("ADMIN_PASSWORD 未设置或仍为默认值，请设置强密码")
            if self.ai_enabled and not self.ai_api_key:
                issues.append("AI_API_KEY 未设置，AI 功能将不可用")
            if not self.cookie_secure:
                issues.append("生产环境 cookie_secure 必须为 True（需要 HTTPS），否则 httpOnly cookie 以明文传输")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                issues.append("SameSite=None 要求 cookie_secure=True，否则浏览器将拒绝 cookie")

        if self.environment == "development":
            if self.secret_key and self.secret_key.startswith("dev-"):
                issues.append("开发模式使用弱 SECRET_KEY（仅本地可接受）")

        return issues


settings = Settings()
