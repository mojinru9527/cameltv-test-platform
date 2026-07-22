---
title: "Batch 32 单一主干迁移 PM 计划"
owner: "pm"
last_reviewed: "2026-07-22"
status: "in_progress"
tags: ["git", "migration", "plan"]
---

# Batch 32 — PM Plan

| Slice | 任务 | 验收标准 | 主要文件/状态 |
|---|---|---|---|
| 1 | 双仓库备份 | bundle/ZIP/哈希/源指纹全部通过 | 仓库外备份目录 |
| 2 | 本地脏内容核对 | 每个文件有去重结论，运行目录不变 | reconciliation 工件 |
| 3 | worktree 工具与 hook | 创建、重复检测、metadata、主干 push 拦截自测通过 | `scripts/git/`, `.githooks/` |
| 4 | 统一 Agent Team 和 CI | 文档以仓库为事实源，PR 门禁全量阻断 | `AGENTS.md`, skill, workflows, Jenkins |
| 5 | 平台全量验证 | 后端/前端/子模块/补丁/凭据检查通过 | QA 报告 |
| 6 | PR #56 合入 | GitHub checks 全绿后 squash merge | GitHub PR #56 |
| 7 | 主干迁移 | baseline tag、`develop→main`、main ruleset | GitHub refs/settings |
| 8 | 旧分支归档 | legacy tag 先验证，再删除 master | GitHub refs/settings |
| 9 | 控制 worktree 验收 | `F:\CamelTv-control` 干净；双 AI 隔离通过；原运行目录指纹不变 | 本地 worktrees |

依赖顺序固定，不并行执行远端重命名和删除。任何校验失败均停在当前可恢复阶段。
