---
title: "Batch 32 单一主干与双 AI 隔离 PRD"
owner: "product"
last_reviewed: "2026-07-22"
status: "approved"
tags: ["git", "worktree", "agent-team"]
---

# Batch 32 — PRD Summary

## 问题

仓库同时存在默认 `develop`、旧 `master` 和文档/CI 中的虚拟 `main`；本地 Claude Code、ChatGPT/Codex 与 Agent Team 还可能共享脏目录。结果是任务基线不一致、未提交代码可能被覆盖、全新 clone 缺少蓝湖子仓库、PR 与部署门禁不一致。

## 成功指标

1. 所有 refs、本地脏文件和 `lanhu-mcp` 脏内容均有经过哈希验证的可恢复备份。
2. 远端只保留一个永久主干 `main`，旧 `develop/master` 均有标签可恢复。
3. `main` 禁止直接 push，必须 PR + required checks；合并策略统一 squash。
4. Claude、Codex 和 Agent Team 能从 `origin/main` 创建独立 worktree，端口、数据库、元数据互不干扰。
5. 当前 `F:\CamelTv` 的文件哈希、脏状态和运行服务不因迁移改变。
6. 全新递归 clone 能初始化固定版本的 `lanhu-mcp`。

## 用户故事

- Given 两个 AI 同时开发不同任务，When 分别创建 worktree，Then 文件、分支、端口和日志互不覆盖。
- Given AI 尝试直接 push 主干，When 执行 push，Then 本地 hook 和 GitHub ruleset 均拒绝。
- Given 新机器 clone 项目，When 使用递归子模块检出，Then 蓝湖 Provider 所需模块可用。
- Given 迁移发生故障，When 使用 baseline/legacy 标签或 bundle/ZIP，Then 可以恢复源码与未提交内容。

## 非目标与 C 条件

- 不解决 npm/Ruff 历史债务、赛事回放缺口或运营后台账号阻塞；这些在主干迁移完成后另开任务分支。
- 不删除或改写当前脏 `lanhu-mcp`；它是平台蓝湖 Provider 依赖。
- 不切换、清理、重启 `F:\CamelTv`。
- C31-3 运营后台账号阻塞继续保留；其余 C 条件不扩展本次 Git 迁移范围。
