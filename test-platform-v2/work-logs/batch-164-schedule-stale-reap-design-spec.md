# Batch 164 — Design Spec

> **Design (🎨)** | Date: 2026-08-12

## 架构决策
后端: TestScheduleRun.heartbeat_at + APScheduler 周期回收任务（5min），阈值 SCHEDULE_STALE_SECONDS=1200（env 可覆盖）；旧数据 NULL 心跳按 started_at 兜底。
## 实现文件
后端: models/test_schedule.py、alembic/versions/20260812_b164_sched_heartbeat.py、core/scheduler.py、core/config.py、tests/test_batch164_schedule_stale.py
## 性能基准
回收任务每 5 分钟一次，单次轻量查询；无热点。
