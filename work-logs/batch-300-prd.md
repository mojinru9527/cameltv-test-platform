# Batch 300（M3 / TA-024）— A4 Failure & Triage Agent：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-300-m3-failure-triage-agent · **基线**：origin/main `6b06d4063`
> **里程碑**：M3 第 9 批

## 1. 问题

失败归因若由模型自由发挥，会出现：编造根因、自填 confidence、甚至“高置信度＝自动关缺陷”。
TA-024 要求：归因只出 draft、证据不足返 UNKNOWN、AI 不得自动关缺陷。

## 2. 目标

1. `FailureTriageAgent`：输出 `execution_outcome / attribution_status / hypotheses`；
2. 12 类归因（含 `UNKNOWN`）；
3. 安全规则：
   - `auto_close_defect` 必须 false，否则拒绝；
   - `human_review_required` 必须 true；
   - `confidence` 必须 null；
   - `UNKNOWN` 归因 ↔ `attribution_status=UNKNOWN` 双向一致；
   - `CROSS_FEATURE_DEFECT` 必须有 supporting_evidence；
4. 100 条标注样本（12 类覆盖）全部正确；
5. 不建表、不改 Run（纯 Agent）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 合法归因 | `test_valid_attribution` |
| A2 | 自动关缺陷拒绝 | `test_auto_close_rejected` |
| A3 | confidence 非 null 拒绝 | `test_confidence_must_be_null` |
| A4 | 必须人工复核 | `test_human_review_required` |
| A5 | UNKNOWN 一致性 | `test_unknown_requires_unknown_status` |
| A6 | CROSS_FEATURE 证据 | `test_cross_feature_requires_evidence` |
| A7 | 空假设拒绝 | `test_empty_hypotheses_rejected` |
| A8 | 100 标注样本 | `test_hundred_labeled_samples` |
| A9 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 LLM（fake 注入）；
- triage_cases/hypotheses 入库（后续表）；
- 缺陷创建/关闭流程（人工审批）。
