# Batch 280（M1 / TA-006）— QA Report

> **部门**：🔍 QA · **日期**：2026-11-10

## 验收

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 1000 事件 seq 连续无重复 | ✅ | `test_1000_events_seq_contiguous`（seq=1..1000，outbox=1000） |
| A2 | producer_event_id 幂等 | ✅ | 同 id 两次只 1 行、同 event.id |
| A3 | 同事务 + 回滚 | ✅ | rollback 后 events/outbox=0；投影失败同样回滚 |
| A4 | schema_version / producer 校验 | ✅ | 缺版本、未知 producer 均抛 `InvalidEventPayload` |
| A5 | dispatch / list after_seq | ✅ | 3 条一次标记、二次 0；after_seq=2 → [3,4,5] |
| A6 | 迁移与回归 | ✅ | up/down/up 0/0/0；1386 passed / 43 skipped；ratchet PASS |

## 命令

```text
pytest tests/test_aiqe_event_service.py -q   → 10 passed
pytest -q                                    → 1386 passed, 43 skipped in 180s
alembic upgrade head / downgrade -1 / upgrade head → 0/0/0
quality_ratchet.py                           → PASS
```

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | ratchet UP037（`Mapped["EventOutbox | None"]` 引号） | 去掉引号 |

## 风险

- SQLite 无 `FOR UPDATE`：高并发下依赖唯一约束兜底；M2 在 PG 上做并发压测；
- 逐类事件 schema 未校验（仅 schema_version），留 M2。

## 判定

A1–A6 全绿，建议 Leader APPROVED。
