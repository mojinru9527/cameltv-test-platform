# Batch 298 — Design / Dev

## 数据

`execution_profiles`：id/project_id/name/purpose/config_json/version/checksum/
approval_status/owner_id/expires_at/created_at（迁移 `20261117`，幂等）。

## 服务

```python
create_profile(...)        # purpose 三档校验；checksum 计算
approve_profile(...)       # approved 后 config/checksum 冻结
profile_checksum(config, purpose, name, version)  # canonical sha256
data_namespace(profile, run_id)                   # iso-<run> / integration / live
acquire_fixture_locks(...) # fixture:<key> 资源锁；失败回滚已占用
start_run_with_profile(...) -> RunProfileScope(namespace, tokens)
finish_run_with_profile(...)  # 释放锁
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-298-1 | checksum 覆盖 purpose/name/version/config | 仅 config 相同不足以复现 profile |
| D-298-2 | core_isolated namespace 带 run_id | 并发 Run 天然隔离 |
| D-298-3 | external_live 禁写共享 fixture | 生产环境 fail-closed |
| D-298-4 | 复用 resource_lock 做 fixture 互斥 | TTL/fencing 已有，不重复造锁 |
| D-298-5 | approved 不可改 | 与 WorkflowDefinition 同策略 |

## 文件

- `app/aiqe/models/profile.py`
- `app/aiqe/services/profile_service.py` / `run_service.py`
- `alembic/versions/20261117_ta022_execution_profiles.py`
- `tests/test_aiqe_execution_profile.py`（7 条）
