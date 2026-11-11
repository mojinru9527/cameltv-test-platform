# Batch 310 — Design / Dev

## 状态机

```text
draft → benchmarked → approved → active
                    ↘ rejected（人工）
```

## 服务

```python
create_candidate(db, project_id, rule, source="bug", duplicate_of=None)
evaluate_candidate(db, id, {false_positive_rate, sample_size, precision?})
approve_candidate(db, id, acknowledge_duplicate=False)
activate_candidate(db, id) -> BugPattern | None
list_candidates(db, project_id)
```

## 护栏

| 护栏 | 实现 |
|------|------|
| 误报率上限 | >0.2 拒绝 |
| 未 benchmark | 拒绝批准 |
| 重复候选 | 必须 acknowledge，否则拒绝 |
| 重复发布 | duplicate_of 或同 pattern_key → 合并，不新增 |
| 未批准激活 | 拒绝 |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-310-1 | benchmark 指标由调用方传入 | 数据管道后续接，先固化门禁 |
| D-310-2 | duplicate 需显式确认 | 防“无提示发布” |
| D-310-3 | 同 key 自动合并 | 双保险，避免并发绕过 |
| D-310-4 | 状态机最小化 | 人审在 approved 之前 |

## 文件

- `app/aiqe/models/learning.py`
- `app/aiqe/services/learning_service.py`
- `alembic/versions/20261122_ta030_learning.py`
- `tests/test_aiqe_learning_curator.py`（10 条）
