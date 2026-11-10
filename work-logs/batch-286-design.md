# Batch 286 — Design / Dev

## 设计

```text
RunContext(db, run_id)
  ├─ output(node_key)            # node_runs.output_ref（同 Run）
  ├─ set_output(node_key, dict)  # 拒绝 ${secrets.*}
  ├─ resolve(value, secrets=...) # 递归；整串保类型；混合串插值
  └─ snapshot(secrets=...)       # 展示/持久化，secret 全脱敏
```

变量命名空间：
- `nodes.<key>.outputs.<name>`：必须存在且同 Run；
- `secrets.<NAME>`：只从 `secrets` mapping 解析；未注入 → `VariableResolutionError`。

调度器：`complete_node(..., outputs={...})` 合并写入 `node_runs.output_ref`。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-286-1 | 输出存 NodeRun.output_ref，不建新表 | 已有字段，M1 迁移已就绪 |
| D-286-2 | secret 由调用方注入 mapping | 不把 Vault 依赖引入 M2 |
| D-286-3 | 整串引用返回原类型 | 下游可用 dict/list 变量 |
| D-286-4 | 写入期拒绝 secret 引用 | fail-closed，避免持久化泄漏 |
| D-286-5 | snapshot 同时按引用与值双重脱敏 | 覆盖间接泄漏 |

## 文件

| 文件 | 说明 |
|------|------|
| `app/aiqe/services/run_context.py` | RunContext + 两类异常 |
| `app/aiqe/services/dag_scheduler.py` | `complete_node(outputs=...)` |
| `tests/test_aiqe_run_context.py` | 9 条单测 |

验证：`pytest -q` → 全量通过（见 QA）；ratchet PASS。
