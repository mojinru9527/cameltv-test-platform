# Batch 294（M3 / TA-019）— Agent Service + A0/A1：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-294-m3-requirement-agent · **基线**：origin/main `8f717fabc`
> **里程碑**：M3 第 4 批

## 1. 问题

需求评估需要 AI 产出验收标准，但模型输出可能不合 schema、编造来源、Key 无效时静默降级。
TA-019 先落 A0 Requirement Agent：严格 schema + source_ref 强约束 + Key 缺失 fail-closed +
执行记录可审计。

## 2. 目标

1. `BaseAgent`：JSON 解析（含 ```json 围栏）、Pydantic 严格校验、无 LLM 抛 `AgentUnavailable`；
2. `RequirementAgent`：输出 summary + acceptance_criteria（每条必须有 `source_ref`）+ risks；
3. `run_agent()`：成功/失败都写 `agent_executions`（状态、模型、输入、输出/错误、时间）；
4. 30 份需求评估集全部通过；
5. 迁移 `20261116`（agent_executions）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 成功执行 + 记录 | `test_run_agent_success_records_execution` |
| A2 | 缺 source_ref 拒绝 | `test_missing_source_ref_rejected` |
| A3 | 非法 JSON 拒绝 | `test_invalid_json_rejected` |
| A4 | 缺 summary 拒绝 / 无 Key fail-closed | `test_missing_summary_rejected_and_missing_llm_fail_closed` |
| A5 | 30 份需求评估集 | `test_thirty_requirement_samples_all_valid` |
| A6 | 围栏 JSON 兼容 | `test_fenced_json_accepted` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 LLM 调用（测试注入 fake；生产接 ai_client）；
- A1 评审、A2 用例设计（后续批次）；
- token 计量/成本（字段已预留）。
