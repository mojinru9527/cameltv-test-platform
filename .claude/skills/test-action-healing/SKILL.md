---
name: test-action-healing
description: 用于 AITDE V3.8 Action Healing（V38-004/005）。Use when applying an approved healing proposal, generating a new CommandPlanVersion, or when the AI must reject an Oracle/Contract/Expected mutation. Triggers: "愈合应用", "healing apply", "action healing", "拟修复应用".
---

# 动作愈合应用（Action Healing Apply）
> AITDE V3.8 V38-004..005。愈合仅允许 **Action-only diff**；Oracle/Contract/Expected 变更整体拒绝。

## 硬不变量

- `HealingPolicy.decide` 只放行 action-only；命中 oracle/contract/expected 键 → REJECT。
- 仅 APPROVED 提案可 apply；apply 时**再跑一次** Policy 作为最终护栏。
- 旧 CommandPlanVersion / 旧 Replay 证据**保留**，产生新版本号。

## 流程

1. `POST /api/v2/healing-proposals/{id}/apply`（approved_by + note）。
2. 返回新 `command_plan_version_id` + `version_no` + `status`。
3. 校验 `old_retained=true`，确认历史未重写。

## 提交前自检

- [ ] 未改动 `expected` / `oracle` / `contract` 字段。
- [ ] 非 APPROVED 提案拒绝 apply。
- [ ] 新版本状态为 VALIDATED，旧版本保留。
