---
title: "ADR-0014 单一 main 主干与 AI Worktree 隔离"
owner: "qa-team"
last_reviewed: "2026-07-22"
status: "accepted"
tags: ["git", "worktree", "agent-team", "ci"]
related: ["AGENTS.md", ".claude/skills/cameltv-agent-team/SKILL.md"]
---

# ADR-0014：单一 `main` 主干与 AI Worktree 隔离

## 背景

仓库长期同时保留 `master` 与默认 `develop`，而 CI、Jenkins 和文档分别引用 `main`、`master`、`develop`。Claude Code、ChatGPT/Codex 和 Agent Team 还可能共享同一脏工作目录，导致未提交内容被切分支、生成物或另一会话覆盖。

## 决策

1. 仅保留 `main` 作为永久主干；旧 `master` 用不可变标签归档，`develop` 直接重命名为 `main`。
2. `main` 禁止直接 push、删除和非快进更新，所有代码通过 PR 和 required checks 合入。
3. 日常分支仅使用 `feature/*`、`fix/*`、`hotfix/*`、`release/*`，默认 squash merge。
4. 每个 AI 任务使用独立 worktree、独立分支、独立 `.ai-worktree.json` 元数据与本地端口；控制 worktree 不运行开发任务。
5. 分支按任务命名；元数据分别记录 workflow（direct/agent-team）和实际 executor（Claude/Codex/human）。Agent Team 是流程而不是执行器，必须在开发前和最终交付前两次向用户确认 Claude 或 Codex；不通过进程名、IDE、客户端、代码风格或 diff 猜测。
6. Agent Team 工件使用唯一 batch 名称和仓库相对路径；仓库文档是共同事实源，路径绑定的 Claude Memory 不作为交付门禁。
7. Claude Code 位于 VS Code、Codex 位于 ChatGPT 客户端不改变 Git 隔离：任务必须使用不同 worktree、分支、端口和本地元数据，禁止两个客户端并行修改同一 worktree。

## 自动执行层

- `start-agent-team-task.ps1 -Executor claude|codex -UserConfirmedExecutor` 只在用户聊天确认后调用，写入 `workflow=agent-team`、实际 executor 和 start confirmed；缺少确认开关时在创建目录/分支前失败。直接任务入口写入 `workflow=direct`。
- 新 worktree 使用 schema v3；Agent Team 初始为 start confirmed/completion pending。schema v1/v2 只做兼容读取，旧 Agent Team 元数据不能通过最终完成确认门禁。
- `confirm-agent-team-completion.ps1` 只在 Draft PR 首轮验证后再次收到用户明确答复时调用；它要求工作区干净、开始身份与完成身份一致，然后写入 completion confirmed。
- `verify-ai-worktree.ps1` 校验 workflow、executor、确认状态、目录、branch、base、scope、端口和干净状态。
- pre-push 对任务分支自动执行 verifier，阻断本地遗漏或 metadata 篡改；任务分支删除和标签不受影响。
- `audit-ai-pr.ps1` 的基础模式允许 completion pending，以便创建 Draft PR 和完成首轮 CI；`-RequireSuccessfulChecks` 对 Agent Team 强制 completion confirmed，并继续核对 workflow/executor、本地/远端 SHA、PR base/head、声明范围、required checks 与 squash-only 策略。
- GitHub Actions 与 main ruleset 是最终不可绕过层；本地工具负责尽早反馈，不能替代远端门禁。

文本文件由 `.gitattributes` 固定 LF（`.bat/.cmd` 除外），仓库配置关闭 `core.autocrlf`，避免 Windows 文件时间或行尾转换制造无内容差异的假脏状态。

## 合并顺序

- 独立模块可以从同一 `origin/main` 并行开发。
- 修改范围重叠或存在依赖时必须串行；后续任务在前序 PR 合入后从新 `origin/main` 创建。
- 已推送的共享任务分支使用 merge 同步 `origin/main`，不以强推 rebase 覆盖其他会话历史。

## 运行环境隔离

每个 worktree 使用独立且不提交的前端端口、后端端口、SQLite 文件和 `.env`。依赖下载缓存可以共享，但 `node_modules`、虚拟环境、构建产物和运行数据库不得跨 worktree 共用。

## 后果

- 优点：唯一可信基线、分支职责清晰、AI 文件隔离、可回滚、CI 与部署语义一致。
- 成本：每个 worktree 需要独立依赖和端口；并行 PR 修改公共追踪文件时仍需按顺序合并。
- 迁移：所有 refs 与脏文件先进入外部 bundle/ZIP；运行中的 `F:\CamelTv` 保持不切分支，由新 `F:\CamelTv-control` 承担主干控制职责。
