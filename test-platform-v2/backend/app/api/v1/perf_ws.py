"""WebSocket endpoint for real-time performance data streaming.

客户端连接后，服务端每 500ms 推送一次性能指标快照。
采集结束时自动推送 session_end 事件并关闭连接。

降级方案：当 WebSocket 不可用时，前端可使用 GET /perf-sessions/{id}/metrics?sinceTs={ts} 轮询。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.perf import PerfSession
from app.services import perf_collector_service as collector
from app.services import perf_service

logger = logging.getLogger("perf.ws")
router = APIRouter()

# 活跃的采集任务: {session_id: {"stop": Event, "ws": WebSocket}}
_active_tasks: dict[int, dict] = {}


async def _collect_loop(session_id: int, ws: WebSocket, planned_duration_s: int) -> None:
    """后台采集循环——每 500ms 采样一次并通过 WebSocket 推送。"""
    db: Session = SessionLocal()
    session = db.get(PerfSession, session_id)

    if not session:
        await ws.send_json({"type": "error", "detail": "会话不存在"})
        db.close()
        return

    device_id = session.device_id
    pkg_name = session.pkg_name
    platform = session.platform
    start_ts = time.time()
    sample_count = 0
    stop_event: asyncio.Event = _active_tasks[session_id]["stop"]

    try:
        while not stop_event.is_set():
            elapsed = time.time() - start_ts

            # 检查是否达到计划时长
            if planned_duration_s > 0 and elapsed >= planned_duration_s:
                break

            try:
                # 调用 SoloX 单次采样（在线程池中运行，避免阻塞事件循环）
                loop = asyncio.get_event_loop()
                snapshot = await loop.run_in_executor(
                    None,
                    collector.collect_single_snapshot,
                    device_id, pkg_name, platform,
                )
            except Exception as exc:
                logger.warning("Snapshot %d failed for session %d: %s", sample_count, session_id, exc)
                snapshot = {"error": str(exc), "events": []}

            now = time.time()
            elapsed_s = now - start_ts

            # 保存到数据库
            try:
                perf_service.save_snapshot(
                    db, session_id, timestamp=now, elapsed_s=elapsed_s, data=snapshot,
                )
            except Exception as exc:
                logger.error("DB save failed for session %d: %s", session_id, exc)

            # WebSocket 推送
            try:
                await ws.send_json({
                    "type": "metrics_snapshot",
                    "session_id": session.session_id,
                    "timestamp": now,
                    "elapsed_s": round(elapsed_s, 1),
                    "sample_index": sample_count,
                    "metrics": snapshot,
                })
            except Exception:
                # 客户端已断开
                break

            sample_count += 1
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        logger.info("Collection cancelled for session %d", session_id)

    finally:
        # 标记采集结束
        reason = "duration_reached" if planned_duration_s > 0 and (time.time() - start_ts) >= planned_duration_s else "user_stop"
        try:
            perf_service.stop_session(db, session_id)
        except Exception as exc:
            logger.error("Failed to stop session %d: %s", session_id, exc)

        # 推送结束通知
        try:
            await ws.send_json({
                "type": "session_end",
                "session_id": session.session_id if session else "",
                "reason": reason,
                "total_samples": sample_count,
                "duration_s": round(time.time() - start_ts, 1),
            })
        except Exception:
            pass

        db.close()
        _active_tasks.pop(session_id, None)
        logger.info("Collection ended for session %d: %d samples, reason=%s", session_id, sample_count, reason)


@router.websocket("/perf-sessions/{session_id}/stream")
async def perf_stream(ws: WebSocket, session_id: int) -> None:
    """WebSocket 性能数据实时推流。

    连接建立后，后端每 500ms 推送一次全量指标快照。
    客户端可发送 {"action": "stop"} 主动停止采集。
    采集达到计划时长或客户端断开时自动结束。
    """
    await ws.accept()

    # 校验会话状态
    db: Session = SessionLocal()
    session = db.get(PerfSession, session_id)
    if not session:
        await ws.send_json({"type": "error", "detail": "会话不存在"})
        await ws.close()
        db.close()
        return

    if session.status != "running":
        await ws.send_json({"type": "error", "detail": f"会话状态为 {session.status}，无法开始采集"})
        await ws.close()
        db.close()
        return

    db.close()

    # 创建停止信号
    stop_event = asyncio.Event()
    _active_tasks[session_id] = {"stop": stop_event, "ws": ws}

    # 启动采集循环
    task = asyncio.create_task(
        _collect_loop(session_id, ws, session.duration)
    )

    try:
        # 监听客户端消息（目前仅支持 stop）
        while True:
            msg = await ws.receive_text()
            try:
                data = json.loads(msg)
                if data.get("action") == "stop":
                    logger.info("Client requested stop for session %d", session_id)
                    stop_event.set()
                    break
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %d", session_id)
        stop_event.set()
    except Exception as exc:
        logger.error("WebSocket error for session %d: %s", session_id, exc)
        stop_event.set()

    # 等待采集任务结束
    try:
        await asyncio.wait_for(task, timeout=10)
    except asyncio.TimeoutError:
        task.cancel()
        logger.warning("Collection task cleanup timed out for session %d", session_id)
