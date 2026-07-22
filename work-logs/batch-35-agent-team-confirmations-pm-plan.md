---
title: "Batch 35 Agent Team 双确认门禁 PM 计划"
owner: "pm"
last_reviewed: "2026-07-22"
status: "active"
tags: ["agent-team", "git", "confirmation"]
---

# 交付切片

| 切片 | 验收标准 | 状态 |
|---|---|---|
| 1 需求与接口 | 六部门工件记录开始确认、两次硬暂停及非目标 | 已完成 |
| 2 红绿测试 | 缺确认、身份错配、脏工作区均拒绝，正确路径通过 | 已完成 |
| 3 脚本与文档 | schema v3、完成确认命令、最终审计门禁及规范同步 | 已完成 |
| 4 真实 PR | Draft PR 首轮 CI 后必须停下等待用户第二次确认 | 进行中 |
| 5 最终交付 | 第二次确认后最终 CI、审计、squash merge 和清理 | 被用户确认阻塞 |

# 质量要求

- PowerShell parser、隔离工具自测、Git hook、YAML、文档保鲜和 `git diff --check` 全部通过。
- 开始确认开关不得触发交互式终端提示；缺失时必须在任何写操作前失败。
- Draft push 与第一轮 CI 可在完成确认 pending 时执行，最终 successful-check 审计必须拒绝 pending。
- 所有 Git 操作仅在 Batch 35 独立 worktree 和 feature 分支进行，不触碰现有测试平台工作区。
