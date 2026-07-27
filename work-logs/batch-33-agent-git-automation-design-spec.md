---
title: "Batch 33 Agent Git 自动审计设计规范"
owner: "design"
last_reviewed: "2026-07-22"
status: "approved"
tags: ["git", "automation", "interface"]
---

# 接口设计

- 身份入口：`start-{claude|codex|agent-team}-task.ps1`，owner 固定，其他创建参数保持一致。
- 本地验证：`verify-ai-worktree.ps1 -RequireMetadata [-ExpectedOwner X] [-RequireClean]`，失败即抛错并返回非零。
- Push 验证：pre-push 只对非删除的任务分支执行 verifier；保护分支永远拒绝；标签和任务分支删除放行。
- PR 验证：`audit-ai-pr.ps1 [-PrNumber N] [-ExpectedOwner X] [-RequireSuccessfulChecks]`，输出 Owner、branch、base、SHA、scope 和三项检查表。
- 远端验证：job 名固定为 `AI/Git 交付策略`，与 ruleset context 完全一致。

# 信任边界

固定入口证明“任务由哪个入口创建”，不证明模型法律身份。GitHub 登录身份、PR 提交者和 required checks 仍由 GitHub 记录和强制。
