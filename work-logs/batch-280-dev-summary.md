# Batch 280（M1 / TA-006）— Dev Summary

> **部门**：🟦 Dev · **日期**：2026-11-10

## 变更文件

| 文件 | 说明 |
|------|------|
| `backend/app/aiqe/models/event.py` | RunEvent + EventOutbox |
| `backend/app/aiqe/models/__init__.py` | 导出新增 |
| `backend/app/aiqe/services/event_service.py` | append_event / list_events / dispatch_outbox / mark_dispatch_failed |
| `backend/app/models/__init__.py` | 注册 event 模型 |
| `backend/alembic/versions/20261112_ta006_run_events.py` | 两表迁移（skip-if-provisioned） |
| `backend/tests/test_aiqe_event_service.py` | 10 条单测 |

## 行为

- `append_event()` 返回 `(event, created)`；重复 `producer_event_id` 返回既有事件且 `created=False`；
- seq 通过锁 Run 行 + `MAX(seq)+1` 分配；`(run_id, seq)` 唯一约束兜底；
- 同事务写 outbox；`project` 回调失败会带走事件与 outbox；
- `dispatch_outbox()` 幂等标记待推送；`list_events(after_seq)` 支持补拉。

## 本地验证

```text
pytest tests/test_aiqe_event_service.py   → 10 passed
pytest -q                                 → 1386 passed / 43 skipped
alembic upgrade/downgrade/upgrade         → 0/0/0
quality_ratchet.py                        → PASS
```
