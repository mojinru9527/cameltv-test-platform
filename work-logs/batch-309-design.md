# Batch 309 — Design / Dev

## 规则

| 域 | 命中关键词 | suites |
|----|-----------|--------|
| auth（强制） | auth/login/permission/rbac/token/session | auth-suite, smoke-suite |
| payment | payment/order/billing | payment-suite, smoke-suite |
| live | live/stream/player/room | live-suite |
| admin | admin/console | admin-suite |
| api | api/、schemas/ | api-suite |
| 未知 | — | smoke-suite |

## 接口

```python
compute_impact(files) -> {impacted_areas, candidate_suites, forced_suites}
ChangeImpactAgent(llm).analyze(files) -> {
  impacted_areas, candidate_suites, forced_suites, rationale
}
```

校验：LLM 输出必须 ⊇ 规则基线（强制 suite、影响域、候选并集），否则 `AgentSchemaError`。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-309-1 | 规则基线先算，LLM 只能补充 | 强制 suite 不漏选 |
| D-309-2 | 未知变化默认 smoke | 保守兜底 |
| D-309-3 | 空 diff 拒绝 | 防误触发全量/空选 |
| D-309-4 | 文件路径匹配而非 AST | PoC 先覆盖高风险关键词 |

## 文件

- `app/aiqe/agents/change_impact_agent.py`
- `tests/test_aiqe_change_impact_agent.py`（7 条）
