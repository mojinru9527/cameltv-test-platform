# Batch 306 — Design / Dev

## 数据

`noise_rules`：id/project_id/pattern/action/scope/expires_at/status/created_by/created_at/updated_at。

## 服务

```python
create_rule(db, project_id, pattern, action="suppress", expires_at=None)
update_rule(db, rule_id, pattern=None, action=None, expires_at=None)
renew_rule(db, rule_id)          # now + 90d
is_effective(rule, now=None)     # active 且未到期
list_rules(db, project_id, include_expired=True)
delete_rule(db, rule_id)
```

## 规则

| 规则 | 实现 |
|------|------|
| 默认 90 天 | `expires_at=None` → now+90d |
| 永久 quarantine | `action=="quarantine"` 且无到期 → 拒绝 |
| 超 90 天 | `expires_at > base+90d` → 拒绝 |
| 到期失效 | `is_effective` 比较 `expires_at` |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-306-1 | 90 天硬上限 | 强制复核，防永久掩盖 |
| D-306-2 | quarantine 必须显式到期 | 最高风险动作 |
| D-306-3 | 过期规则保留在列表 | 便于人工复核/续期 |
| D-306-4 | 前端只做展示表格 | CRUD 页面后续接入 |

## 文件

- `app/aiqe/models/noise_rule.py`
- `app/aiqe/services/noise_rule_service.py`
- `alembic/versions/20261121_ta0273_noise_rules.py`
- `frontend/src/pages/defect/NoiseRuleTable.tsx`
- tests: backend 8 + frontend 2
