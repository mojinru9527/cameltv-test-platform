---
title: "Batch 34 Agent Team 执行器身份模型 Leader 判决"
owner: "leader"
last_reviewed: "2026-07-22"
status: "pending"
tags: ["leader", "agent-team", "git"]
---

# 判决

`PENDING`。只有新身份模型自测、真实 PR 基础审计、required checks 和最终审计都有可复现证据后，才可改为 `APPROVED`。

# 抽检重点

- Agent Team 是 workflow，而不是 executor。
- 实际执行器必须显式为 Claude Code 或 Codex，不能声称自动猜测。
- 旧 owner-only worktree 保持兼容但不得伪造未知执行器。
