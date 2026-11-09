# Batch 280（M1 / TA-006）— Event Collector + Outbox：PRD

> **部门**：🟦 Product · **日期**：2026-11-10 · **批次模式**：完整
> **分支**：feature/batch-280-m1-event-outbox · **基线**：origin/main `10c0f9213`

## 1. 问题

Run 有了事实源（batch-279），但执行过程没有 append-only 事件流：无法回放、无法 SSE 推送、
无法证明"浏览器看到的执行过程 = 数据库事实"。TA-006 要求 events + outbox 同事务、seq 严格递增、
producer_event_id 幂等。

## 2. 目标

1. `run_events`（append-only，`(run_id, seq)` 唯一）+ `event_outbox`（1:1，待推送标记）；
2. `append_event()` 单入口：校验 producer/payload、幂等、锁 Run 行分配 seq、写 outbox、可选投影，
   全部在同一事务内，只 flush 不 commit；
3. `dispatch_outbox()` 标记已推送；`list_events(after_seq)` 支持断线补拉；
4. 1000 事件 seq 连续无重复；重发同 producer_event_id 不入库。

## 3. 验收标准

| # | 标准 | 证据 |
|---|------|------|
| A1 | 1000 事件 seq=1..1000 无重复 | `test_1000_events_seq_contiguous` |
| A2 | 同 producer_event_id 重发只入库一次 | `test_duplicate_producer_event_id_is_idempotent` |
| A3 | 事件 + outbox + 投影同事务；回滚全消失 | `test_rollback...` / `test_projection_*` |
| A4 | payload 必须带 schema_version；未知 producer 拒绝 | `test_payload_requires...` / `test_unknown_producer...` |
| A5 | dispatch 只标记一次；list after_seq 正确 | `test_dispatch...` / `test_list_events...` |
| A6 | 迁移 up/down/up + 全量回归 | QA 记录 |

## 4. 非目标

- SSE HTTP 端点 / Redis PubSub 实际推送（batch-282 前端联调时接入）；
- 19 类事件的 payload schema 全集（只强制 schema_version，逐类 schema 在 M2 补）；
- 跨 Run 全局 seq（按 Run 严格递增即可）。

## 5. 风险

| 风险 | 缓解 |
|------|------|
| SQLite 无 `FOR UPDATE` | 单写者 + 唯一约束兜底；PG 行锁保证并发 |
| 初始迁移 create_all 预建表 | 迁移检测 `seq` 列后跳过（D-280-2） |
| outbox 积压 | dispatcher 分批 + retry_count/last_error 可观测 |
