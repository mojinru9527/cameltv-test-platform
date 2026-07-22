---
title: "Batch 34 Agent Team 执行器身份接口规范"
owner: "design"
last_reviewed: "2026-07-22"
status: "ready"
tags: ["agent-team", "git", "interface"]
---

# 身份接口

新元数据格式：

```json
{
  "schema_version": 2,
  "workflow": "agent-team",
  "executor": "codex"
}
```

约束：

- `workflow`: `direct | agent-team`
- `executor`: `claude | codex | human`；Agent Team 入口仅接受 `claude | codex`
- 目录：`{executor}-{task}`；分支仍按业务任务命名，不包含 AI 名称
- `owner`：仅旧元数据兼容读取，新任务不再写入

# 命令接口

```powershell
./scripts/git/start-agent-team-task.ps1 -Executor codex -Kind feature -Task batch-34-example -Scope test-platform-v2 -FrontendPort 5214 -BackendPort 8214
./scripts/git/verify-ai-worktree.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireMetadata
./scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks
```

# 状态与错误

- 缺少 Agent Team executor：参数绑定失败，不创建目录或分支。
- workflow/executor 错配：校验失败，pre-push 阻断。
- owner-only 元数据：标记为 schema 1；Claude/Codex/human 推导为 direct，旧 agent-team 的 executor 标记 unknown，不伪造判断。
- 不提供自动进程识别；调用方必须显式声明当前宿主。

# 设计签核

无 UI 变更。接口规范与用户纠正后的角色模型一致，允许进入 Dev。
