---
name: test-action-healing-review
description: 用于 AITDE V3.3 Action Healing 提案评审（V33-011）。Use when reviewing a healing proposal before/after Command IR diff, deciding approve/reject, or when the AI must reject an Oracle/Contract mutation. Triggers: "愈合评审", "action healing review", "批准/拒绝愈合提案", "Oracle 变更守卫", "healing proposal".
---

# Action Healing 评审（Action Healing Review）

> AITDE V3.3 V33-011。愈合只允许 **Action-only diff**；任何修改 Oracle 或 Frozen Contract 的提案**整体拒绝并记录审计**。

## 硬不变量

- `oracle_changes = []`、`contract_changes = []`（`action_healing_v1` 强制）
- 若模型返回 Oracle 修改，提案整体拒绝并进入 Audit，**绝不部分放行**
- Runtime/Environment 问题，绝不伪装成 BUSINESS_FAIL

## 评审流程

1. 加载提案：`GET /api/v2/healing-proposals?scenario_adapter_id=...&status=OPEN`
2. 对比 `before_json` / `after_json` 的 Command IR 差异
3. 显示 Oracle 守卫（`OracleChangeGuardBadge`）：`oracleChanged=true` 必须显式暴露
4. 批准 / 拒绝：
   - 仅 OPEN 且 action-only 可批准：`POST /api/v2/healing-proposals/{id}/approve`
   - 拒绝：`POST /api/v2/healing-proposals/{id}/reject`
   - 已 REJECTED 的 Oracle 篡改提案**不可翻转**为 APPROVED（服务端 409）

## Locator 修复范围

只允许以下 Action 变更（§4 优先级）：

- data-testid → role+name → label → semantic text → CSS（最后）
- 等待策略、同流程内的导航目标、其它非业务动作

## 提交前自检

- [ ] 对比 diff 中驱动为 `assertion` / `oracle` 的命令是否被改
- [ ] 若有改动：标记 REJECTED + Audit，禁止批准
- [ ] 仅 action-only 差异才走 approve
