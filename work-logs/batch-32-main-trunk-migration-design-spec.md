---
title: "Batch 32 Git/Worktree 设计规范"
owner: "design"
last_reviewed: "2026-07-22"
status: "approved"
tags: ["git", "worktree", "developer-experience"]
---

# Batch 32 — Design Spec

## 信息架构

```text
origin/main
├── F:\CamelTv-control                         main；只 fetch/pull/创建 worktree
└── F:\CamelTv-worktrees\{owner}-{task}       task branch；独立开发和测试
    └── .ai-worktree.json                     ignored；owner/scope/ports/base
```

`F:\CamelTv` 是迁移前运行/脏工作区，保留到用户决定退役，不作为新控制目录。

## 工具契约

- `new-ai-worktree.ps1`：接收 owner/kind/task/scope/ports，必须从精确 `origin/main` 创建。
- `verify-ai-worktree.ps1`：拒绝 protected/detached/非法分支，报告领先落后和活跃 worktree。
- `install-git-guardrails.ps1`：仅写仓库 local config，设置 GitHub 身份、prune、push/current、rerere 和 hooksPath。
- `.githooks/pre-push`：阻断目标 `main/master/develop`，不阻断 task branch/tag。

## 冲突与日志

- batch 名称和分支必须唯一；脚本检查本地与远端重名。
- 同一文件范围不得并行；有依赖时等待前序 PR 合入后从新 `origin/main` 创建。
- `work-logs` 使用仓库相对链接；个人 Memory 不参与合并门禁。
- 每个 worktree 使用不同前后端端口与 SQLite，不共享运行产物。
