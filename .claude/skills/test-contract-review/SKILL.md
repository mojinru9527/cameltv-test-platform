---
name: test-contract-review
description: Use when reviewing or freezing an AITDE Test Contract — "评审契约", "冻结契约", "contract review", "freeze contract". Checks the freeze preconditions (scope complete, no open P0/P1 ambiguity) and that rules are backed by approved scope/intent.
---

# AITDE 契约评审（Test Contract Review）

## 目标
在 Contract 进入 **FROZEN** 前，检查「什么才算正确」是否成立且可追溯。

## Freeze 前置条件（不满足 → 409 CONTRACT_PRECONDITION_FAILED）
- [ ] Scope 已完成评审（review_progress == 1.0）
- [ ] 无未解决的 P0/P1 Ambiguity
- [ ] 每条 rule 与 required_outcome 都源于已批准 Scope / Intent，且带 source_refs

## 评审清单
- **规则可追溯**：`rule_key` 有明确 business 依据（来源 + Tester 批准）。
- **禁止 AI 臆造的 Oracle**：`AI_INFERRED` 不能直接成为 `required` 且已批准的 Oracle（Oracle Guard）。
- **语句可验证**：statement 是客观、可断言的条件，不是主观描述。

## 冻结交互
- 冻结后：AI 不能修改业务预期；后续修改只能通过 `ChangeProposal` 生成 v+1 版本。
- 前端显示「冻结后 AI 不能修改预期 + 后续走 Proposal」让 Tester 明确确认。

## 关键纪律
- Contract 一旦 FROZEN 不可变（repo + service 双层保护）。
- 评审通过 ≠ 冻结；冻结是一个显式、需确认的操作。
