# Batch 295（M3 / TA-020）— A2 Test Design / Review Agent：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-295-m3-test-design-agent · **基线**：origin/main `24b69b750`
> **里程碑**：M3 第 5 批

## 1. 问题

A0 产出验收标准后，需要 A2 设计/评审用例。风险：P0 用例没有验收断言、旧用例已覆盖却重复新增、
reject 不给理由。

## 2. 目标

1. `TestDesignAgent`：输出 `decision(approve/reject/skip) + cases + coverage_notes/reject_reason`；
2. 每条 P0 用例必须带 `acceptance_refs`；
3. `coverage_sufficient=True` 时只允许 `skip`（cases 为空 + coverage_notes），禁止重复新增；
4. `reject` 必须有原因且不带 cases；schema 非法一律拒绝；
5. 50 份需求评估集全部通过。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | P0 带验收引用可批准 | `test_approve_with_p0_acceptance_refs` |
| A2 | P0 无引用拒绝 | `test_p0_without_acceptance_refs_rejected` |
| A3 | 覆盖充分时禁止重复新增 | `test_covered_requires_skip_not_duplicate` |
| A4 | skip 不得带 cases | `test_skip_with_cases_rejected` |
| A5 | reject 需原因 | `test_reject_requires_reason_and_no_cases` |
| A6 | schema 非法拒绝 | `test_invalid_schema_rejected` |
| A7 | 50 样本集 | `test_fifty_requirement_samples_all_valid` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 LLM 调用（fake 注入）；
- 与现有用例库的语义去重（`duplicate_of` 预留）；
- A3 Workflow Planner（下一批）。
