"""UI test ORM models — UiTestJob + UiTestRun."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class UiTestJob(Base):
    __tablename__ = "ui_test_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    test_spec: Mapped[str] = mapped_column(String(500), default="")      # path to test file
    browser: Mapped[str] = mapped_column(String(20), default="chromium")  # chromium/firefox/webkit
    environment_id: Mapped[int | None] = mapped_column(default=None, index=True)  # 执行环境
    status: Mapped[str] = mapped_column(String(20), default="idle")       # idle/running/done/fail
    last_result: Mapped[str] = mapped_column(Text, default="{}")          # JSON summary
    creator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    runs: Mapped[list["UiTestRun"]] = relationship(
        "UiTestRun", back_populates="job",
        cascade="all, delete-orphan", order_by="UiTestRun.started_at.desc()",
    )


class UiTestRun(Base):
    __tablename__ = "ui_test_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ui_test_job.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")    # pending/running/done/fail/cancelled
    result: Mapped[str] = mapped_column(Text, default="{}")               # JSON: {total,pass_,fail,skip,duration}
    screenshots: Mapped[str] = mapped_column(Text, default="[]")          # JSON array
    video_url: Mapped[str] = mapped_column(String(500), default="")
    trace_id: Mapped[str] = mapped_column(String(100), default="")
    base_url: Mapped[str] = mapped_column(String(500), default="")        # 执行时 BASE_URL 快照
    artifact_dir: Mapped[str] = mapped_column(String(500), default="")    # 产物目录路径
    report_json_path: Mapped[str] = mapped_column(String(500), default="")  # report.json 路径
    html_report_path: Mapped[str] = mapped_column(String(500), default="")  # HTML 报告路径
    error_message: Mapped[str] = mapped_column(Text, default="")          # 错误信息
    stdout: Mapped[str] = mapped_column(Text, default="")                 # 捕获的标准输出
    stderr: Mapped[str] = mapped_column(Text, default="")                 # 捕获的标准错误
    process_id: Mapped[int | None] = mapped_column(Integer, default=None) # 运行中 Playwright 进程 PID
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False) # 是否请求取消
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    job: Mapped["UiTestJob"] = relationship("UiTestJob", back_populates="runs")


class UiTestScript(Base):
    """UI 脚本资产 — 可被 UiTestJob 引用的 Playwright 脚本。"""
    __tablename__ = "ui_test_script"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    script_key: Mapped[str] = mapped_column(String(200), default="", index=True)  # 稳定唯一键
    spec_path: Mapped[str] = mapped_column(String(500), default="")               # Playwright spec 路径
    module: Mapped[str] = mapped_column(String(100), default="")                  # 业务模块
    owner: Mapped[str] = mapped_column(String(100), default="")                   # 负责人
    tags: Mapped[str] = mapped_column(Text, default="[]")                         # JSON array
    status: Mapped[str] = mapped_column(String(20), default="active")             # active/disabled/deprecated
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
