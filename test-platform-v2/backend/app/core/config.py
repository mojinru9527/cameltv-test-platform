"""Application settings loaded from environment variables.

Security: ALL sensitive values (secret_key, passwords, API keys) MUST be
provided via environment variables or .env file in production.
Default empty values will cause a startup validation error in production mode.
"""
from __future__ import annotations

import os
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

    # ── Database ──
    database_url: str = "sqlite:///./data/platform.db"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_create_tables: bool = True

    # ── Default admin ──
    admin_username: str = "admin"
    admin_password: str = ""                   # production: required; dev falls back to "admin123"

    # ── ELK ──
    elk_base_url: str = ""
    elk_index: str = "*"

    # ── AI / LLM ──
    ai_enabled: bool = True
    ai_api_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""                       # production: required
    ai_model: str = "deepseek-chat"
    ai_max_tokens: int = 8192
    ai_temperature: float = 0.3

    # ── File paths (configurable for portability) ──
    workspace_root: str = ""      # empty = auto-detect from app/services/__file__
    skill_dir: str = ""           # test-case-design skill directory
    lanhu_mcp_dir: str = ""       # lanhu-mcp module directory
    data_dir: str = ""            # extracted data cache directory

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @cached_property
    def effective_admin_password(self) -> str:
        """Dev convenience: fall back to a dev-only default when unconfigured."""
        if self.admin_password:
            return self.admin_password
        if self.environment == "development":
            return "admin123"
        return ""  # production will fail validation

    @cached_property
    def effective_secret_key(self) -> str:
        if self.secret_key:
            return self.secret_key
        if self.environment == "development":
            return "dev-secret-do-not-use-in-prod"
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

        if self.environment == "development":
            if self.secret_key and self.secret_key.startswith("dev-"):
                issues.append("开发模式使用弱 SECRET_KEY（仅本地可接受）")

        return issues


settings = Settings()
