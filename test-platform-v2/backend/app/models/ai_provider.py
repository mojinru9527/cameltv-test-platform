"""AI 提供方配置（项目级）—— Batch A（AI 模型配置中心）。"""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiProvider(Base, TimestampMixin):
    __tablename__ = "ai_provider"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(100))  # 展示名（如 "DeepSeek 官方"）
    provider_type: Mapped[str] = mapped_column(
        String(30), default="openai_compatible"
    )  # deepseek_official | openai_compatible
    api_base_url: Mapped[str] = mapped_column(String(500), default="")
    api_key_encrypted: Mapped[str] = mapped_column(
        Text, default=""
    )  # Fernet 加密，绝不落明文
    models: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组（模型清单）
    default_model: Mapped[str] = mapped_column(String(100), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # 每项目至多一个
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
