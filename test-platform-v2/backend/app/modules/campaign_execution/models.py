from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class TestCampaign(Base):
    __tablename__ = "test_campaign"
    __table_args__ = (UniqueConstraint("project_id", "name", "version", name="uq_campaign_project_name_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(32), default="adhoc")
    requirement_version: Mapped[str] = mapped_column(String(128), default="")
    environment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    dataset_id: Mapped[int | None] = mapped_column(Integer, default=None)
    runner_selector_json: Mapped[str] = mapped_column(Text, default="{}")
    strategy_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class CampaignItem(Base):
    __tablename__ = "test_campaign_item"
    __table_args__ = (UniqueConstraint("campaign_id", "sequence", name="uq_campaign_item_sequence"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("test_campaign.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    asset_id: Mapped[int] = mapped_column(Integer, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    depends_on_json: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
