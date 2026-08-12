# Batch 164 — PM Plan

> **PM (🟨)** | Date: 2026-08-12

## 规格摘要
**原始需求**: PRD §1（C163-1）  **目标时间**: 0.5d

## 开发任务
### [ ] T1: Schema + 模型 + 迁移（test_schedule_run.heartbeat_at）
**验收**: alembic 裸库 upgrade 成功，幂等（重复列跳过）；revision ≤32。
**涉及文件**: backend/models/test_schedule.py、alembic/versions/20260812_b164_sched_heartbeat.py

### [ ] T2: 心跳 + 回收 watchdog
**验收**: _execute_schedule 开始/结束更新 heartbeat_at；reap_stale_schedule_runs 每 5 分钟回收失联 run（含 NULL 心跳兼容）；回收后可再次触发。
**涉及文件**: backend/core/scheduler.py、backend/core/config.py（SCHEDULE_STALE_SECONDS）

### [ ] T3: 回归测试
**验收**: stale 回收 / 新鲜保留 / NULL 心跳 / 可重入 4 项。
**涉及文件**: backend/tests/test_batch164_schedule_stale.py

## 质量要求
- [ ] Alembic 单头 + 裸库 upgrade  - [ ] ruff F821  - [ ] 后端全量 pytest  - [ ] 无前端改动
