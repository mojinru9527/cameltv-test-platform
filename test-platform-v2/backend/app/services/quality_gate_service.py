"""质量门禁配置服务（从 report_service 抽离，报告中心删除后独立保留）。

质量门禁是「版本验收/发布结论」的核心口径，项目级配置存于 ``quality_gate_config`` 表；
本模块只保留配置读写两个函数（原 ``report_service.get/save_quality_gate_config`` 逐字迁移）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quality_gate import QualityGateConfig


def get_quality_gate_config(db: Session, project_id: int) -> dict | None:
    """Get quality gate config for a project. Returns None if not configured."""
    row = db.scalar(
        select(QualityGateConfig).where(QualityGateConfig.project_id == project_id)
    )
    if not row:
        return None
    return {
        "id": row.id,
        "project_id": row.project_id,
        "pass_rate_threshold": row.pass_rate_threshold,
        "p0_max": row.p0_max,
        "p1_max": row.p1_max,
        "coverage_threshold": getattr(row, "coverage_threshold", 0),
        "max_failed_cases": getattr(row, "max_failed_cases", 0),
        "max_blocked_cases": getattr(row, "max_blocked_cases", 0),
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def save_quality_gate_config(db: Session, project_id: int, data: dict) -> dict:
    """Create or update quality gate config for a project. Returns the config dict."""
    row = db.scalar(
        select(QualityGateConfig).where(QualityGateConfig.project_id == project_id)
    )

    _settable = (
        "pass_rate_threshold", "p0_max", "p1_max",
        "coverage_threshold", "max_failed_cases", "max_blocked_cases",
        "enabled",
    )
    if row:
        for k in _settable:
            if k in data and data[k] is not None:
                setattr(row, k, data[k])
    else:
        row = QualityGateConfig(
            project_id=project_id,
            pass_rate_threshold=data.get("pass_rate_threshold", 80),
            p0_max=data.get("p0_max", 0),
            p1_max=data.get("p1_max", 5),
            coverage_threshold=data.get("coverage_threshold", 0),
            max_failed_cases=data.get("max_failed_cases", 0),
            max_blocked_cases=data.get("max_blocked_cases", 0),
            enabled=data.get("enabled", True),
        )
        db.add(row)

    db.flush()
    db.refresh(row)

    return {
        "id": row.id,
        "project_id": row.project_id,
        "pass_rate_threshold": row.pass_rate_threshold,
        "p0_max": row.p0_max,
        "p1_max": row.p1_max,
        "coverage_threshold": getattr(row, "coverage_threshold", 0),
        "max_failed_cases": getattr(row, "max_failed_cases", 0),
        "max_blocked_cases": getattr(row, "max_blocked_cases", 0),
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
