# Batch 303 — Design / Dev

## 数据

`triage_experiments`：id / triage_case_id / hypothesis_id / experiment_key / changed_variable /
changed_value / profile_id / verification_run_id / idempotency_key(unique) / status / created_at。

## 实验

| key | 语义 |
|-----|------|
| E1 | replay_same_env |
| E2 | disable_feature_flag |
| E3 | isolated_profile |
| E4 | reset_test_data |
| E5 | isolate_concurrency |
| E6 | normalize_network |

## 服务

```python
run_experiment(db, experiment_key, change, idempotency_key,
               triage_case_id, hypothesis_id, profile_id, verification_run_id) -> TriageExperiment
list_experiments(db, triage_case_id)
validate_change(change)  # 必须 len==1
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-303-1 | change 严格单键 | 双变量结论不可归因 |
| D-303-2 | idempotency_key 唯一约束 + 先查 | 重复调用不产生新验证 Run |
| D-303-3 | verification_run_id 允许显式传入 | 调度器可先建 Run 再登记实验 |
| D-303-4 | profile_id 外键 SET NULL | profile 删除不丢实验历史 |

## 文件

- `app/aiqe/models/triage.py`
- `app/aiqe/services/triage_service.py`
- `alembic/versions/20261118_ta025_triage_experiments.py`
- `tests/test_aiqe_triage_experiments.py`（7 条）
