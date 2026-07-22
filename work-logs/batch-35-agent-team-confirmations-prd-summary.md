---
title: "Batch 35 Agent Team 双确认门禁 PRD"
owner: "product"
last_reviewed: "2026-07-23"
status: "approved"
tags: ["agent-team", "git", "confirmation"]
---

# 问题陈述

Agent Team 已能显式记录 Claude Code 或 Codex 执行器，但任务启动脚本本身仍无法证明用户在开发前确认过身份，也没有在交付前再次核对实际执行器。用户要求 Agent Team 在任务开始前发起问询、等待答复，开发和首轮验证后再次问询；未经第二次确认不得进入最终审计或合并。

# 本批次开始确认

| 字段 | 记录 |
|---|---|
| 用户确认的执行器 | `codex` |
| 使用入口 | ChatGPT/Codex 桌面客户端 |
| 确认日期 | 2026-07-22 |
| 状态 | 已确认，可开始 Batch 35 |

Claude Code 使用 VS Code 插件、Codex 使用 ChatGPT 客户端不会影响隔离。隔离边界由独立 Git worktree、任务分支、端口和本地元数据提供；客户端只决定谁在对应路径执行命令。

# 本批次完成确认

| 字段 | 记录 |
|---|---|
| 用户确认的实际执行器 | `codex` |
| 最终交付授权 | 已授权最终审计、Ready 与 squash 合并 |
| 确认时间 | 2026-07-23 00:14:17 +08:00 |
| 前置证据 | PR #60 首轮 7/7 checks 全绿，pending 按预期阻断最终审计 |

# 成功指标

| 指标 | 目标 |
|---|---:|
| 未经开始确认即创建 Agent Team worktree | 0 |
| 执行器不一致仍能完成确认 | 0 |
| 未经结束确认通过最终 Agent Team 审计 | 0 |
| schema v1/v2 读取兼容 | 100% |

# 用户故事与验收标准

- 作为任务发起人，我希望 Agent Team 在创建开发环境前问我使用 Claude Code 还是 Codex。
  - Given 尚未收到聊天答复 / When 启动 Agent Team / Then 不创建目录或分支。
- 作为任务发起人，我希望开发结束后再核对实际执行器。
  - Given Draft PR 和首轮 CI 已完成 / When 未确认结束身份 / Then 最终审计和合并被阻止。
- 作为负责人，我希望两次身份一致且可审计。
  - Given 开始为 Codex / When 尝试以 Claude 确认完成 / Then 命令拒绝且元数据不变。

# 非目标与 C 条件

- 不自动从进程名、IDE、客户端、提交风格或代码内容猜测执行器。
- 不修改测试平台业务代码、UI、路由或 Agent Team log 路由。
- 不提交本地 `.ai-worktree.json`。
- `C-CONDITIONS.md` 当前全部 Open 项均为平台业务或环境条件，与本次 Git 门禁无关，全部明确豁免。
