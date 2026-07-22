---
title: "Batch 34 Agent Team 执行器身份模型 PRD"
owner: "product"
last_reviewed: "2026-07-22"
status: "approved"
tags: ["agent-team", "git", "identity"]
---

# 问题陈述

当前规则把 Agent Team、Claude Code、Codex 作为并列 owner，导致 `owner=agent-team` 无法回答“实际由哪个 AI 修改代码”。用户需要 Agent Team 继续负责六部门流程，同时能够声明、校验并审计实际执行器。

# 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|---|---:|---:|---|
| Agent Team 分支可识别实际执行器 | 0% | 100% 新建任务 | 本批次自测与真实 PR |
| 错误 workflow/executor 被本地校验拒绝 | 不支持 | 2 类错配均拒绝 | 自测 |
| 旧 worktree 推送兼容 | owner-only | 不因升级突然中断 | 自测 |

# 非目标

- 不尝试通过进程名、代码风格或提交内容猜测 AI；这些信号不可靠。
- 不把本地 `.ai-worktree.json` 提交到 GitHub。
- 不修改 `test-platform-v2/` 业务代码或处理现有 C 条件；`C-CONDITIONS.md` 的全部 Open 项均与本次 Git 身份基础设施无关，明确豁免。

# 用户故事与验收标准

- 作为 Agent Team 使用者，我希望启动任务时选择 Claude Code 或 Codex，以便后续审计知道实际执行器。
  - Given 从控制仓库启动 Agent Team / When 指定 `-Executor codex` / Then 元数据为 `workflow=agent-team`、`executor=codex`。
- 作为 Leader，我希望同时校验流程和执行器，以便错误入口不能获得批准。
  - Given Agent Team/Codex 元数据 / When 期望 Claude 或 direct / Then 校验失败并阻止交付。
- 作为旧任务维护者，我希望 owner-only 元数据不会突然失效。
  - Given 合法旧元数据 / When pre-push 校验 / Then 在兼容模式下继续工作，并清楚标识为 legacy。

# 技术考量与上线

使用版本化本地元数据，目录继续以前缀执行器隔离。先通过本地自测，再用 Draft PR 验证远端门禁；检查全绿后 squash 合入 main。
