# Batch 164 — C163-1 调度 stale 回收/heartbeat QA 报告

> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 6（回收 4 + 门禁 + 迁移） | 6 | 0 | 0 |

## 可执行门禁
- ruff F821 ✅ | pytest 全量 **1393 passed / 0 failed / 3 skipped** ✅
- alembic 裸库 upgrade → 单头 `20260812_b164_sched_heartbeat` ✅（幂等迁移）

## 逐条件（C163-1）
- 模型：`test_schedule_run.heartbeat_at`（幂等迁移，revision 29 字符）。
- 心跳：`_execute_schedule` 开始/完成/失败均更新 heartbeat_at。
- 回收：`reap_stale_schedule_runs`（启动即跑 + 每 5 分钟）按 heartbeat_at（NULL 时 started_at 兜底）回收超过 `SCHEDULE_STALE_SECONDS`（默认 1200s）的 running run → failed + 明确错误；回收后可再次触发。
- 测试：stale 回收 / 新鲜保留 / NULL 心跳兜底 / 触发后回收可重入（4 个）✅。

## 发布建议
状态: READY ✅（生产复验：run#9 自动回收 → 15.0.0 调度可再次触发）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 0.5d vs 0.5d | 0/0/0/0 | 1（测试会话注入） | 后台线程与测试库隔离 | 周期任务函数支持注入会话便于测试 |
