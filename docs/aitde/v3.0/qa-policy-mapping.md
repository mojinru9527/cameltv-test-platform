# AITDE V3.0 QA 规范 → Scenario 映射

> 说明：AITDE 平台现有的测试规范（`functional-checklist`、`api-checklist`、`case-template`）仍然是 QA 事实源。V3.0 把「承载对象」从 `TestCase` 迁移到 `TestScenario + Oracle`，因此需要明确哪些规则进入 Scenario Designer。

## 映射总览

| 规范来源 | 是否进入 Scenario Designer | 说明 |
| --- | --- | --- |
| `functional-checklist.md` | 部分 | 功能点覆盖率、正/负/边界、状态机、闭环、权限/端差异 → 进入 `Scenario` 的 `given/when/expected` 与 `TestOracle(Given/When/Then)` 建模 |
| `api-checklist.md` | 部分 | 入参校验、业务逻辑校验、返回值校验、接口闭环 → 作为 `ApiAdapter` 的 Oracle 输入 |
| `case-template.md` | 是（投影） | 用例字段（标题/前提/步骤/预期/优先级）作为 `FunctionalView` 投影模板；不再作为 core 事实源 |
| `tests/test-case-standards/` 权威输出要求 | 是（投影） | 功能/接口用例输出要求投影到 Functional View 展示 |

## 进入 Scenario Designer 的规则

1. **覆盖基线**：每个需求功能点 ≥ 1 条 Scenario；正面 + 负面 + 边界。
2. **Given/When/Then**：契约 rule → Scenario 的 `given`/`when`/`expected_state`；Oracle 从 `expected_state` 派生态势/接口/DB 断言。
3. **深度层**：状态机 × 用户视角 × 闭环 × 关联 × 权限/端差异 → 生成更多 Scenario（与 oracle_type 对应）。
4. **Oracle 类型**：`UI/API/DB/EVENT/LOG/CONTRACT/VISUAL/PERFORMANCE`；V3.0 仅建模（不执行）。

## 不进入 Scenario Designer（仍属资产/评审）

- `TestCase` 编辑与历史追溯（兼容期）。
- 人工执行的模板步骤本身（作为 Functional View 投影，不改变 Scenario 语义）。
- AI_INFERRED Oracle 的最终取舍（保留给 Tester 评审，Oracle Guard）。

## 结论
V3.0 不丢弃现有规范，而是把它**投影**到 Scenario / Functional View 上；同一业务的 canonical source of truth 变为「Contract + Scenario」。
