# Batch 306（M4 / TA-027.3）— Noise Suppression Rules：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-306-m4-noise-rules · **基线**：origin/main `7653840f4`
> **里程碑**：M4 第 4 批

## 1. 问题

噪音抑制规则若不设到期时间，会永久掩盖真实缺陷；`quarantine` 尤其危险。TA-027.3 要求
**90 天强制复核**、**永久 quarantine 被拒**。

## 2. 目标

1. `noise_rules` 表 + 迁移 `20261121`（pattern/action/scope/expires_at/status）；
2. 默认到期 = 创建 + 90 天；显式到期不得超过 90 天；
3. `quarantine` 必须给到期时间（null 直接拒绝）；
4. `renew_rule` 重置 90 天并激活；`is_effective` 到期即失效；
5. 前端 `NoiseRuleTable` 展示规则/动作/到期/状态。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 默认 90 天 | `test_default_expiry_is_90_days` |
| A2 | 永久 quarantine 拒绝 | `test_permanent_quarantine_rejected` |
| A3 | 超 90 天拒绝 | `test_expiry_over_90_days_rejected` |
| A4 | 到期失效 | `test_expired_rule_not_effective` |
| A5 | 续期 90 天 | `test_renew_extends_90_days` |
| A6 | 更新规则 | `test_update_pattern_and_action` |
| A7 | 删除/非法输入 | `test_delete_rule` / `test_invalid_action_and_empty_pattern` |
| A8 | 前端表格 | `NoiseRuleTable.test.tsx`（2） |
| A9 | 全量 | backend/frontend + ratchet |

## 4. 非目标

- 规则 CRUD 独立页面路由（表格组件已备）；
- 规则命中统计/自动续期提醒。
