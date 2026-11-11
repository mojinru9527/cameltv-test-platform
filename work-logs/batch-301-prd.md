# Batch 301（M3 / TA-024.2）— Noise Hint Agent：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-301-m3-noise-hint-agent · **基线**：origin/main `64639f908`
> **里程碑**：M3 第 10 批（收口前）

## 1. 问题

真实失败里常有噪音（广告抖动、feature flag、并发 Run 抢资源、环境漂移、数据残留）。
A4 归因之后需要一层“疑似噪音”提示，但不能替人下结论或自动关缺陷。

## 2. 目标

1. `.claude/skills/noise-hint-agent/SKILL.md`：Skill 说明（何时用、输入、输出、规则、示例）；
2. `NoiseHintAgent`：1-3 条 hint，每条 `suspected_factor + evidence_refs`；
3. 证据引用前缀限制：`artifact: / event: / flag: / run: / signal:`；
4. 安全：`auto_close_defect=false`、`human_review_required=true`；
5. 证据不足 → `UNKNOWN`。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 广告抖动样本输出 hint+证据 | `test_ad_jitter_sample_with_evidence` |
| A2 | 最多 3 条 | `test_at_most_three_hints` |
| A3 | 空证据拒绝 | `test_empty_evidence_rejected` |
| A4 | 非法证据前缀拒绝 | `test_invalid_evidence_prefix_rejected` |
| A5 | 禁止自动关缺陷 | `test_auto_close_rejected` |
| A6 | 必须人工复核 | `test_human_review_required` |
| A7 | UNKNOWN 兜底 | `test_unknown_factor_allowed` |
| A8 | 0 条拒绝 | `test_zero_hints_rejected` |
| A9 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 Skill 运行时（Claude skill 文件 + Python 参考实现）；
- 自动降噪/关缺陷；
- 与 triage 表联动。
