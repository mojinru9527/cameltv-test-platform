"""环境与变量管理模型 — 项目级环境配置与加密变量。"""
from __future__ import annotations

from sqlalchemy import UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class Environment(Base, TimestampMixin):
    __tablename__ = "environment"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column()                          # e.g. "开发环境"
    env_type: Mapped[str] = mapped_column(default="test")        # dev / test / staging / prod
    base_url: Mapped[str] = mapped_column(default="")            # https://api.example.com
    description: Mapped[str] = mapped_column(default="")


class EnvironmentVariable(Base, TimestampMixin):
    __tablename__ = "environment_variable"
    __table_args__ = (UniqueConstraint("environment_id", "key", name="uq_env_var_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[int] = mapped_column(index=True)
    key: Mapped[str] = mapped_column()                           # variable name, e.g. "BASE_URL"
    value: Mapped[str] = mapped_column(Text, default="")         # plain or encrypted
    encrypted: Mapped[bool] = mapped_column(default=False)       # whether value is AES encrypted
    description: Mapped[str] = mapped_column(default="")
