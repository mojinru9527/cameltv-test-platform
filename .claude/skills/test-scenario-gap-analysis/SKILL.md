---
name: test-scenario-gap-analysis
description: 用于 AITDE V3.8 Scenario Gap 分析（V38-010）。Use when detecting scenario gap candidates, converting a gap to a Contract/Scenario change proposal, or when the AI must not write a formal Scenario Expected. Triggers: "场景缺口", "scenario gap", "gap analysis", "缺口分析".
---

# 场景缺口分析（Scenario Gap Analysis）
> AITDE V3.8 V38-010。Gap 只产出 **proposal**，绝不直接写正式 Scenario Expected。

## 硬不变量

- 输出 `scenario_gap_candidate`（proposal only）。
- Gap → 正式 Scenario 必须走：Tester Review → Contract/Scenario Change Proposal → New Version。
- 不得绕过审批把 gap 直接写进 `scenario_versions`。

## 流程

1. `GET /api/v2/missions/{id}/scenario-gaps` → 已有 Gap 候选。
2. `POST /api/v2/scenario-gaps/{id}/convert` → 转为 Change Proposal（title + risk_level）。
3. 校验返回 `note` 含 "proposal only"，且不可重复转换。

## 提交前自检

- [ ] 未写正式 Scenario Expected。
- [ ] 转换必须走 Review/Version。
- [ ] 已转换的 Gap 不重复转换。
