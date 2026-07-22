---
title: "Batch 35 Agent Team 双确认门禁 Leader 判决"
owner: "leader"
last_reviewed: "2026-07-22"
status: "pending"
tags: ["leader", "agent-team", "git", "confirmation"]
---

# 当前判决

`PENDING`。开始确认有效，但在以下全部条件完成前不得批准或合并：

1. 本地红绿测试和静态检查全部通过；
2. Draft PR 首轮检查全部通过；
3. pending 状态确实阻断最终 Agent Team 审计；
4. Agent Team 再次向用户确认实际执行器和最终审计/合并授权；
5. 用户第二次确认后记录 completion evidence，并让新提交的 required checks 全绿；
6. 最终审计通过且 PR 保持可合并。

# 抽检重点

- 不允许以客户端或 IDE 自动猜测身份。
- 不允许用 schema v1/v2 降级绕过 Agent Team 结束确认。
- 第二次确认前只允许 Draft PR 和首轮验证，不允许 Ready、最终批准或合并。
