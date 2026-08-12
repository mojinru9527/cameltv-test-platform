# Batch 164 — C163-1 调度运行 stale 回收 / heartbeat（PRD）

> **Product (🟦)** | Date: 2026-08-12 | Status: Draft | Mode: full（含 Schema：test_schedule_run.heartbeat_at）

## 1. 问题陈述
调度运行记录可能永久卡 `running`：15.0.0 调度 run#9 自 14:46 起卡运行超 1h（execute_all 长计划异常/超时未更新 run），导致：
- 状态失真（页面一直“执行中”）；
- `already_running` 判定永久阻塞该调度后续触发。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| stale running 回收 | 永久卡住 | 超过阈值（默认 1200s）自动标记 failed，可再次触发 |
| 心跳 | 无 | 运行开始/结束时写入 heartbeat_at |

## 3. 非目标
- 不实现长计划拆分/取消（沿用现有执行）。
- 不改变 execute_all_cases 语义。

## 4. 用户故事 + 验收
- As 测试人员, I want 失联的调度运行被自动回收, so that 调度可再次触发。验收：构造 stale run → 回收任务将其置 failed → 再次触发成功。
- As 测试人员, I want 运行记录有心跳, so that 回收判定可靠。验收：运行中 heartbeat_at 非空且新鲜。

## 5. 技术考量
- 模型：TestScheduleRun.heartbeat_at（DateTime nullable，幂等迁移）。
- 调度器：`_execute_schedule` 开始/结束更新 heartbeat_at；新增周期任务 `reap_stale_schedule_runs`（每 5 分钟，启动即跑一次），阈值 `SCHEDULE_STALE_SECONDS`（默认 1200；兼容旧数据：heartbeat_at 为 NULL 时按 started_at 判定）。
- 测试：stale 回收 / 新鲜保留 / NULL 心跳兼容 / 触发可重入。

## 6. 上线计划
合入 + 部署 → 生产复验：run#9 自动回收 → 15.0.0 调度再次触发成功。

## 7. 技能使用
cameltv-bug-guard（迁移幂等/后台任务）
