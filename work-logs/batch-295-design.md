# Batch 295 — Design / Dev

## 接口

```python
TestDesignAgent(llm).run_design(
    assessment: dict,
    existing_cases: list[dict] | None,
    coverage_sufficient: bool = False,
) -> {
    "decision": "approve|reject|skip",
    "cases": [{title, priority, steps, acceptance_refs}],
    "coverage_notes": str,
    "reject_reason": str,
    "duplicate_of": [str],
}
```

## 校验规则

| 规则 | 处理 |
|------|------|
| P0 用例无 acceptance_refs | `AgentSchemaError` |
| approve + coverage_sufficient | 拒绝（应 skip） |
| skip + cases 非空 / 无 coverage_notes | 拒绝 |
| reject 无 reject_reason / 带 cases | 拒绝 |
| schema 非法 | 拒绝 |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-295-1 | 覆盖充分由调用方传入 | 去重需要用例库检索，PoC 先固化接口 |
| D-295-2 | P0 断言引用强校验 | 对齐“P0 无验收断言不得批” |
| D-295-3 | skip 与 approve 互斥 | 防止“已覆盖仍新增” |
| D-295-4 | 50 样本用 fake LLM 跑 | 评测可重复、不依赖 Key/网络 |

## 文件

- `app/aiqe/agents/test_design_agent.py`
- `tests/test_aiqe_test_design_agent.py`（7 条，含 50 样本）
