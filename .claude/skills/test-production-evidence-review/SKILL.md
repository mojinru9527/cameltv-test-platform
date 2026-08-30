---
name: test-production-evidence-review
description: 用于 AITDE V3.6 Production Evidence 评审。Use when reviewing an observed journey / XHR evidence / real-state discovery, or deciding whether production behaviour implies a scenario/contract change. 生产证据只产生 Proposal（auto_approved=false），绝不自动冻结 Contract。Triggers: "生产证据评审", "production evidence review", "真实状态发现", "observed journey review", "XHR evidence review", "gap analysis".
---

# 生产证据评审（Production Evidence Review）

> AITDE V3.6 V36-012。Production 是 Evidence Source，不是主 Test Runtime。AI 只负责总结、找冲突、出 Proposal；**绝不**把生产行为当标准，**绝不**自动冻结 Contract。

## 硬不变量

- **Production 默认只读**：只允许 Browser Observe / ReadOnly Explore / HTTP GET/HEAD / 明确 allowlist 的查询型 POST / DB SELECT only。
- **AI 不拥有 PASS/FAIL 裁决权**：正式结论只由 Required Oracle + Deterministic Assertion + Evidence 链路给出。
- **生产证据只产生 Proposal（`auto_approved=false`）**：任何 Gap / Ambiguity / Scope Change / Scenario Gap 都必须是候选；缺少 `auto_approved:false` 即非法，整条拒绝并记审计。
- **绝不自动冻结 Contract**：生产观察到的行为永远只是「证据」，不是「应该如此」；Contract 变更必须走人审。

## 评审流程

1. 取观察会话/旅程：`GET /api/v2/production/observation-sessions/{id}`、`GET /api/v2/production/journeys/{id}`。
2. 用 `journey_summary_v1` 把步骤总结为**有序、只读、无密**摘要。
3. 用 `production_evidence_gap_analysis_v1` 找 Contract/现状冲突，产出 Proposal（`auto_approved:false`）。
4. 用 `entity_graph_explanation_v1` 解释实体图（如有）。
5. 调用 `POST /api/v2/production/evidence/{journey_id}/analyze-gaps` 生成 Gap Proposal；前端 `GapCandidatePanel` 展示候选，**供人工确认**，AI 不点「approve」。

## 提交前自检

- [ ] 输出的每个 Proposal `.auto_approved === false`
- [ ] 未把生产行为写进 / 提升为 Frozen Contract
- [ ] 未执行任何生产写操作（无下单/支付/退款/建单；无 DDL/写库）
- [ ] 摘要 / 说明中没有原始 `Authorization` / `Cookie` / `token`，未暴露 PII
- [ ] 已用 `ProdReadOnlyBanner` 语义确认页面处于 `PRODUCTION / READ ONLY`
