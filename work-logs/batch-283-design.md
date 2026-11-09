# Batch 283（M2 / TA-009）— Design

> **部门**：🟪 Design · **日期**：2026-11-10

## 校验流水线

```text
validate_workflow(graph, registered_drivers, registered_capabilities)
  ├─ schema_version / nodes 非空
  ├─ node key 唯一、depends_on 存在、禁止自依赖
  ├─ 环检测（Kahn 拓扑）
  ├─ edges 端点存在且必须出现在 depends_on
  ├─ driver / capability 注册表校验
  ├─ 写操作 + max_attempts>1 → 必须 idempotency_key_expr / compensation_node
  ├─ assertion expected / expected_ref（exploratory 豁免）
  └─ 变量引用 ${nodes.X.outputs.Y}：X 必须传递祖先 + Y 已声明
→ 聚合全部 issue 后一次抛 WorkflowValidationError
```

## API

```python
validate_workflow(graph, *, registered_drivers, registered_capabilities=None) -> None
workflow_checksum(graph) -> str   # canonical JSON 的 sha256
```

`WorkflowValidationError.issues: list[ValidationIssue(code, message, node)]`
供 API 返回结构化 422（TA-010 接入时实现）。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-283-1 | 一次聚合全部 issue 再抛 | 前端/CI 一次修完，避免逐条挤牙膏 |
| D-283-2 | capability 注册表可选 | 先支持 driver 准入；capability 在 TA-015 注册表落地后强制 |
| D-283-3 | 写操作判定 = HTTP method 或 `type=cleanup` | 覆盖当前样本；driver 级写语义后续扩展 |
| D-283-4 | checksum 用 canonical JSON（sort_keys + 紧凑分隔符） | 内容固定、可复现，不随键顺序变化 |
| D-283-5 | 规则 6/7 的审批流留 TA-010 | 本批只做“可拒绝”的静态校验 |
