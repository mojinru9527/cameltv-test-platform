# Batch 309（M5 / TA-029）— A5 Change Impact：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-309-m5-change-impact · **基线**：origin/main `7aa541f12`
> **里程碑**：**M5 第 1 批**

## 1. 问题

PR diff 变化时若只挑“相关”用例，公共权限/登录改动容易漏掉鉴权回归。TA-029 要求：
候选回归并集**强制包含**受影响 suite，公共权限/登录变化不得漏选。

## 2. 目标

1. `compute_impact(files)`：文件路径 → 影响域 + 候选 suite + 强制 suite；
2. 规则：auth/login/permission/rbac/token/session → `auth-suite + smoke-suite`（强制）；
   live/payment/admin/api 各自 suite；未知 → `smoke-suite`；
3. `ChangeImpactAgent`：LLM 输出必须覆盖强制 suite 与影响域，否则拒绝；
4. 空文件列表拒绝。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | auth 强制 auth+smoke | `test_auth_change_forces_auth_and_smoke` |
| A2 | 多域并集 | `test_union_of_multiple_areas` |
| A3 | 未知默认 smoke | `test_unknown_change_defaults_to_smoke` |
| A4 | 合法输出 | `test_valid_agent_output` |
| A5 | 漏强制 suite 拒绝 | `test_omitted_forced_suite_rejected` |
| A6 | 漏 auth 域拒绝 | `test_omitted_auth_area_rejected` |
| A7 | 空 diff 拒绝 | `test_empty_files_rejected` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 suite 选择器/用例库检索（规则层先保证不漏）；
- diff 语义解析（按文件路径/关键词）。
