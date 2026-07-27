"""Performance monitoring REST API — session CRUD + device listing + report + compare."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R
from app.schemas.perf import (
    CompareRequest,
    CompareResponse,
    DeviceListResponse,
    MetricTimeseriesResponse,
    PerfDeviceOut,
    PerfReportResponse,
    PerfSessionCreate,
    PerfSessionListResponse,
    PerfSessionOut,
)
from app.services import perf_service

logger = logging.getLogger("perf")
router = APIRouter(prefix="/perf-sessions", tags=["性能测试"])


# ── Device ──

@router.get("/devices", response_model=R[DeviceListResponse])
def list_devices(
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Any:
    """列出当前 PC 连接的 Android/iOS 设备。"""
    devices = perf_service.list_devices(db)
    device_outs = [PerfDeviceOut(**d) for d in devices]
    return R.ok(data=DeviceListResponse(devices=device_outs))


# ── Session CRUD ──

@router.post("", response_model=R[PerfSessionOut])
def create_session(
    data: PerfSessionCreate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("perftest:create")),
) -> Any:
    """创建性能采集会话。"""
    session = perf_service.create_session(db, data, creator_id=current.user.id, project_id=current.project_id or 0)
    return R.ok(data=session)


@router.get("", response_model=R[PerfSessionListResponse])
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: str | None = Query(None),
    device_id: str | None = Query(None),
    pkg_name: str | None = Query(None),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("perftest:list")),
) -> Any:
    """分页查询采集会话列表。"""
    items, total = perf_service.list_sessions(
        db, current.project_id or 0, page=page, page_size=page_size,
        platform=platform, device_id=device_id, pkg_name=pkg_name,
    )
    return R.ok(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{session_id}", response_model=R[PerfSessionOut])
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:list")),
) -> Any:
    """获取指定会话详情。"""
    session = perf_service.get_session(db, session_id)
    if not session:
        raise APIException(code=404, msg="会话不存在")
    return R.ok(data=session)


@router.delete("/{session_id}", response_model=R[dict])
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:delete")),
) -> Any:
    """删除采集会话及关联指标数据。"""
    session = perf_service.get_session(db, session_id)
    if not session:
        raise APIException(code=404, msg="会话不存在")
    db.delete(session)
    db.commit()
    return R.ok(data={"detail": "ok"})


# ── Session Control ──

@router.post("/{session_id}/start", response_model=R[dict])
def start_session(
    session_id: int,
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:execute")),
) -> Any:
    """启动采集会话。"""
    session = perf_service.start_session(db, session_id)
    if not session:
        raise APIException(code=400, msg="会话不存在或状态不允许启动")
    return R.ok(data={
        "status": "running",
        "started_at": session.started_at.isoformat() if session.started_at else None,
    })


@router.post("/{session_id}/stop", response_model=R[dict])
def stop_session(
    session_id: int,
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:execute")),
) -> Any:
    """停止采集会话。"""
    session = perf_service.stop_session(db, session_id)
    if not session:
        raise APIException(code=404, msg="会话不存在")
    return R.ok(data={
        "status": session.status,
        "duration_s": session.actual_duration_s,
    })


# ── Metrics ──

@router.get("/{session_id}/metrics", response_model=R[MetricTimeseriesResponse])
def get_metrics(
    session_id: int,
    since_ts: float = Query(0, alias="sinceTs"),
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:list")),
) -> Any:
    """获取会话时序数据点。"""
    session = perf_service.get_session(db, session_id)
    if not session:
        raise APIException(code=404, msg="会话不存在")

    metrics = perf_service.get_metrics(db, session_id, since_ts=since_ts)
    points = []
    for m in metrics:
        try:
            values = json.loads(m.data_json)
        except (json.JSONDecodeError, TypeError):
            values = {}
        points.append({
            "timestamp": m.timestamp,
            "elapsed_s": m.elapsed_s,
            "values": values,
        })

    return R.ok(data={
        "session_id": session.session_id,
        "metrics": points,
        "total_points": len(points),
    })


# ── Report ──

@router.get("/{session_id}/report", response_model=R[PerfReportResponse])
def get_report(
    session_id: int,
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:report")),
) -> Any:
    """获取采集报告。"""
    report = perf_service.get_report(db, session_id)
    if not report:
        raise APIException(code=404, msg="会话不存在或无数据")
    return R.ok(data=report)


# ── Compare ──

@router.post("/compare", response_model=R[CompareResponse])
def compare_sessions(
    data: CompareRequest,
    db: Session = Depends(get_db),
    _current: CurrentUser = Depends(require_permission("perftest:report")),
) -> Any:
    """对比两次采集会话。"""
    result = perf_service.compare_sessions(db, data.session_a_id, data.session_b_id)
    if not result:
        raise APIException(code=404, msg="会话不存在或无数据")
    return R.ok(data=result)
