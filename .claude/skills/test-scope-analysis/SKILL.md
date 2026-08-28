---
name: test-scope-analysis
description: Use when generating or reviewing an AITDE test scope — "分析测试范围", "分析范围", "scope", "测试范围". Produces ScopeItem candidates where every item MUST carry source refs, strict enums, and a 0..1 confidence, then hands off to Tester review.
---

# AITDE 测试范围分析（Test Scope Analysis）

## 目标
把一个 Mission 的 Sources（解析后的片段）转成**结构化 Scope 候选**，供 Tester 评审。这是「AI 到底要测什么」的第一道关口。

## 输入
- Mission 已关联并解析的 Sources（PRD / OpenAPI / 补充说明的 fragments）。

## 强制输出契约（严格）
每个 ScopeItem 必须满足：
```json
{
  "scope_key": "kebab-case-key",
  "scope_type": "FEATURE|BUSINESS_FLOW|PAGE|API|DATA_STATE|RISK|REGRESSION_AREA",
  "name": "readable",
  "decision": "INCLUDE|EXCLUDE",
  "test_depth": "FULL|REGRESSION|SMOKE|OBSERVE",
  "risk_level": "P0|P1|P2|P3",
  "reason": "为什么纳入",
  "confidence": 0.0,
  "source_refs": [{"artifact_id": 1, "fragment_id": 2, "location": "PRD 3.2"}]
}
```
- **source_refs 必填**：每条都必须指向真实 Source fragment；AI 不能引用不存在的 source。
- **confidence ∈ [0,1]**；枚举闭合；reason 要有依据（来源 + 历史缺陷 + Schema 变化）。
- **不得臆造**：超出输入 Sources 的项不得生成。

## 工作流
1. 收集该 Mission 的解析片段，作为上下文。
2. 逐片段/逐业务点生成 ScopeItem。
3. 交给 Tester Review（approve/reject/改深度）。
4. 全部评审完成后 Scope 才可 `complete`。

## 关键纪律
- AI 只产候选，**评审权在 Tester**。
- 低 confidence 或涉及"是否纳入"的项应同步生成 Ambiguity，交给后续 Contract 前置处理。
