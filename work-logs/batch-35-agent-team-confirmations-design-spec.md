---
title: "Batch 35 Agent Team 双确认门禁设计规范"
owner: "design"
last_reviewed: "2026-07-22"
status: "ready"
tags: ["agent-team", "git", "confirmation"]
---

# 元数据接口

Agent Team 新任务使用 schema v3：

```json
{
  "schema_version": 3,
  "workflow": "agent-team",
  "executor": "codex",
  "confirmations": {
    "start": {
      "status": "confirmed",
      "executor": "codex",
      "confirmed_at": "2026-07-22T00:00:00.0000000+08:00"
    },
    "completion": {
      "status": "pending",
      "executor": null,
      "confirmed_at": null
    }
  }
}
```

约束：

- `start.status` 必须为 `confirmed`，且 executor 与顶层一致。
- `completion.status` 只能为 `pending|confirmed`；confirmed 时 executor 与开始身份一致且必须带时间。
- schema v1/v2 保持读取兼容，但旧 Agent Team 元数据不能通过最终确认门禁。
- direct workflow 不需要双确认；本次门禁只作用于 Agent Team。

# 命令接口

```powershell
./scripts/git/start-agent-team-task.ps1 -Executor codex -UserConfirmedExecutor -Kind feature -Task example -Scope scripts/git
./scripts/git/confirm-agent-team-completion.ps1 -Executor codex -UserConfirmedCompletion
./scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks
```

布尔开关表示“Agent Team 已在聊天中收到用户明确答复”，脚本本身不弹终端问询。规范要求调用方先问、停下、等待，再传入开关。

# 状态机

`未确认 → 开始确认 → 开发/提交/Draft PR/首轮 CI → 完成待确认 → 完成确认 → 最终审计/Ready/合并`

- 未确认：不得创建 Agent Team worktree。
- 完成待确认：允许基本 PR 审计，不允许最终 successful-check 审计。
- 完成确认：仅在工作区干净、身份匹配且用户已明确授权后写入。

# 客户端与隔离

VS Code 中的 Claude Code 和 ChatGPT 客户端中的 Codex 可以并行使用。二者必须进入不同 worktree；分支、目录、端口和元数据提供隔离，IDE/客户端不会改变 Git 的隔离语义。
