# Batch 280（M1 / TA-006）— Design

> **部门**：🟪 Design · **日期**：2026-11-10

## 1. 表

| 表 | 主键 | 约束 | 说明 |
|----|------|------|------|
| `run_events` | UUID string(36) | `uq(run_id, seq)`、`uq(run_id, producer_event_id)`；索引 `(run_id, seq)` | append-only；payload JSON 必带 schema_version |
| `event_outbox` | BIGINT（SQLite variant INTEGER） | `uq(run_event_id)` | 与事件 1:1；`dispatched_at` 标记、`retry_count`、`last_error` |

外键：`run_id → test_runs`（CASCADE）、`node_run_id / step_attempt_id`（SET NULL）、
`run_event_id → run_events`（CASCADE）。

## 2. 写入流程（`append_event`）

```text
validate producer / event_type / payload.schema_version
  → SELECT test_runs WHERE id=:run FOR UPDATE      (锁 Run，串行化 seq)
  → if producer_event_id 已存在: return (existing, False)   (幂等)
  → seq = MAX(seq)+1
  → INSERT run_events
  → INSERT event_outbox(run_event_id)
  → 可选 project(db, event)                        (投影 node/step，同事务)
  → flush（不 commit）
```

调用方负责 commit/rollback；投影抛异常 → 整体回滚（A3 已验证）。

## 3. 读取 / 推送

- `list_events(run_id, after_seq, limit)`：seq 升序，供 SSE 断线补拉；
- `dispatch_outbox(limit)`：把 `dispatched_at IS NULL` 的前 N 条打标并 `retry_count+1`；
- `mark_dispatch_failed(outbox_id, error)`：记录失败与错误（供 dispatcher 重试）。

## 4. 设计决策

| ID | 决策 | 理由 |
|----|------|------|
| D-280-1 | outbox id 用 `BigInteger().with_variant(Integer,"sqlite")` | PG BIGINT、SQLite 走 rowid 自增 |
| D-280-2 | 迁移检测 `run_events.seq` 已存在则跳过 | 初始 `create_all` 会预建（同 279） |
| D-280-3 | 只强制 `schema_version`，逐类 payload schema 后续补 | 先保证可回放，不阻塞 M1；TA-004.2 的逐类校验在 M2 |
| D-280-4 | 幂等只按 `(run_id, producer_event_id)`，null 不参与 | 与规格唯一索引一致 |

## 5. 与 spec 的差异

无表结构差异；`run_events.payload_json` 增加"MUST schema_version"的运行时校验，
属于 TA-004.2 的前置落点，已在 §4.11 注记。
