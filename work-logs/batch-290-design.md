# Batch 290 — Design / Dev

## 表

`node_capability_manifests`（`node_id` 唯一）：
`driver_key/version`、`capabilities_json`、`platforms_json`、`max_parallel_sessions`、
`artifact_types_json`、`last_evidence_ref`、`last_heartbeat_at`、`available`、`created/updated_at`。

## 服务

```python
register_manifest(...)   # upsert；available = bool(evidence_ref) and bool(caps)
record_evidence(...)     # 实测 evidence 回填，available 重新计算
supports(node_id, cap)   # available and cap in caps
select_nodes(required)   # available 且 required ⊆ caps（缺一不可）
known_capabilities()     # browser.*/api.http/db.readonly/device.*…
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-290-1 | 自描述 + evidence 双门槛 | 防止“声明有 WebKit 实际没有” |
| D-290-2 | 能力列表存 JSON、选择在 Python 侧过滤 | SQLite/PG JSON 包含语法差异大，MVP 简单可靠 |
| D-290-3 | capabilities 允许项目扩展 key | 标准集用于校验器，扩展不阻塞接入 |
| D-290-4 | 迁移幂等（表已存在则跳过） | 与 create_all 预建兼容 |

## 文件

- `app/aiqe/models/capability.py`
- `app/aiqe/services/capability_registry.py`
- `alembic/versions/20261115_ta015_capability_manifests.py`
- `tests/test_aiqe_capability_registry.py`（8 条）
