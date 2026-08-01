from __future__ import annotations

import math
import threading

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.av_check import AvCheckTask
from app.schemas.av_check import AvCheckMeasurementCreate
from app.services import av_check_service


def _task(db_session) -> AvCheckTask:
    task = AvCheckTask(
        project_id=1,
        task_id="AV-TEST-001",
        name="视频延迟采集",
        protocol="HLS",
        creator_id=1,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_create_measurement_calculates_real_statistics(db_session):
    task = _task(db_session)
    samples = [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100]
    result = av_check_service.create_measurement(
        db_session,
        task.id,
        project_id=1,
        creator_id=1,
        data=AvCheckMeasurementCreate(
            metric_type="video_delay",
            scenario="公司 5GHz WiFi",
            method="OCR 时间戳",
            samples=samples,
            threshold=2000,
            network_condition="5GHz / 无丢包",
            device_info="OBS + Chrome",
        ),
    )

    assert result["sample_count"] == 12
    assert result["mean"] == pytest.approx(1550.0)
    assert result["median"] == pytest.approx(1550.0)
    assert result["min"] == 1000
    assert result["max"] == 2100
    assert result["p95"] == pytest.approx(2045.0)
    assert result["pass_basis"] == "p95"
    assert result["passed"] is False
    assert result["simulated"] is False


def test_frame_rate_uses_mean_and_greater_than_comparison(db_session):
    task = _task(db_session)
    result = av_check_service.create_measurement(
        db_session,
        task.id,
        project_id=1,
        creator_id=1,
        data=AvCheckMeasurementCreate(
            metric_type="frame_rate",
            samples=[24, 25, 26],
            threshold=24,
        ),
    )

    assert result["comparator"] == ">="
    assert result["pass_basis"] == "mean"
    assert result["passed"] is True


def test_unknown_metric_and_non_finite_samples_are_rejected():
    with pytest.raises(ValueError, match="不支持的指标类型"):
        AvCheckMeasurementCreate(metric_type="random_metric", samples=[1], threshold=1)

    with pytest.raises(ValueError, match="有限数值"):
        AvCheckMeasurementCreate(metric_type="video_delay", samples=[math.nan], threshold=1)


def test_measurements_are_project_isolated(db_session):
    task = _task(db_session)
    with pytest.raises(ValueError, match="任务不存在"):
        av_check_service.create_measurement(
            db_session,
            task.id,
            project_id=2,
            creator_id=1,
            data=AvCheckMeasurementCreate(
                metric_type="video_delay",
                samples=[1000],
                threshold=2000,
            ),
        )


def test_running_probe_is_not_started_twice(db_session, monkeypatch):
    task = _task(db_session)
    task.stream_url = "https://sports.example.test/live.m3u8"
    task.status = "running"
    db_session.commit()

    started_threads: list[str] = []

    class ThreadSpy:
        def __init__(self, *args, name: str, **kwargs):
            started_threads.append(name)

        def start(self):
            return None

    monkeypatch.setattr(threading, "Thread", ThreadSpy)
    monkeypatch.setattr(
        "app.services.ffmpeg_service._check_ffmpeg_installed",
        lambda: (True, "test"),
    )

    result = av_check_service.trigger_check(db_session, task.id, project_id=1)

    assert result["status"] == "running"
    assert started_threads == []


def test_running_trigger_does_not_emit_terminal_notifications(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    task = _task(db_session)
    task.stream_url = "https://sports.example.test/live.m3u8"
    db_session.commit()
    task_data = av_check_service.get_task(db_session, task.id, project_id=1)
    assert task_data is not None
    task_data["status"] = "running"

    events: list[str] = []
    monkeypatch.setattr(
        "app.services.notify_service.queue_notification",
        lambda project_id, event, data: events.append(event),
    )
    monkeypatch.setattr(
        av_check_service,
        "trigger_check",
        lambda db, task_id, project_id: task_data,
    )

    response = client.post(
        f"/api/v1/av-checks/{task.id}/trigger",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert events == ["task_started"]


def test_background_probe_emits_terminal_notifications_after_commit(db_session, monkeypatch):
    task = _task(db_session)
    task.stream_url = "https://sports.example.test/live.m3u8"
    db_session.commit()

    events: list[tuple[str, dict]] = []

    class ImmediateThread:
        def __init__(self, *, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(threading, "Thread", ImmediateThread)
    monkeypatch.setattr(
        "app.services.ffmpeg_service._check_ffmpeg_installed",
        lambda: (True, "test"),
    )
    monkeypatch.setattr(
        "app.services.ffmpeg_service.probe_stream",
        lambda stream_url, protocol: {
            "ok": True,
            "metrics": [
                {
                    "name": "首帧时间",
                    "value": 800,
                    "threshold": 1000,
                    "passed": True,
                    "unit": "ms",
                    "recommended": "<= 1000ms",
                    "raw_value": 800,
                },
            ],
            "raw": {"ffprobe_version": "test"},
        },
    )
    monkeypatch.setattr(
        "app.core.db.SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        "app.services.notify_service.queue_notification",
        lambda project_id, event, data: events.append((event, data)),
    )

    result = av_check_service.trigger_check(db_session, task.id, project_id=1)

    assert result["status"] == "running"
    assert [event for event, _ in events] == ["task_finished", "test_result"]
    assert events[0][1]["status"] == "done"
    assert events[1][1]["conclusion"] == "通过"
