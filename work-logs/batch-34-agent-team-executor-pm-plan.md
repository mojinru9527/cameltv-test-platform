---
title: "Batch 34 Agent Team 执行器身份模型 PM 计划"
owner: "pm"
last_reviewed: "2026-07-22"
status: "active"
tags: ["agent-team", "git", "identity"]
---

# 规格摘要

将 Agent Team 从执行者改为 workflow，并用 executor 表示 Claude Code/Codex；兼容旧 owner-only worktree。

# 开发任务

| 任务 | 验收标准 | 文件 |
|---|---|---|
| 1 红测 | 新 workflow/executor 断言在旧实现上失败 | `scripts/git/test-ai-worktree-tools.ps1` |
| 2 元数据 V2 | 新任务写入 schema/workflow/executor，Agent Team 强制选择执行器 | `new-ai-worktree.ps1`、三个 start 脚本 |
| 3 验证与审计 | workflow/executor 正反例、legacy 兼容、push 拦截通过 | `verify-ai-worktree.ps1`、`audit-ai-pr.ps1`、hook |
| 4 规范同步 | 文档不再把 Agent Team 当成实际 AI | `AGENTS.md`、skill、ADR、PR 模板 |
| 5 远端交付 | Draft PR、三项 required checks、最终审计与 squash 合入 | Batch 34 QA/Leader/看板 |

# 质量要求

- PowerShell 语法解析、隔离工具自测、Git hook 语法、YAML 解析和 `git diff --check` 全部通过。
- 真实分支 push 必须通过新版 pre-push；PR 必须通过仓库全部检查。
- 不触碰测试平台业务文件及原开发工作区。
