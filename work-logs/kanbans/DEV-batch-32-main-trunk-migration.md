---
title: "DEV Batch 32 单一主干迁移看板"
owner: "dev"
last_reviewed: "2026-07-22"
status: "active"
tags: ["kanban", "git", "worktree"]
---

# DEV Batch 32 — Main Trunk Migration

| Slice | 状态 | 证据/下一步 |
|---|---|---|
| 1 备份 | ✅ | `F:\CamelTv-safe-backup\20260722-201657`，bundle/ZIP/hash 全绿 |
| 2 本地核对 | ✅ | reconciliation 工件；原目录不动 |
| 3 worktree 工具 | ✅ | 自测 PASS |
| 4 Agent/CI/Jenkins | ✅ | 单一 main 规范、隔离工具、CI 门禁与 Jenkins fail-fast 已落地 |
| 5 全量测试/PR | 🔄 | 本地后端 653/前端 96 全绿；等待 PR #56 远端 CI |
| 6 baseline/rename | ⏳ | 等待 PR 合入 |
| 7 ruleset/legacy | ⏳ | 等待 main 建立 |
| 8 控制 worktree/验收 | ⏳ | 最后执行 |

风险：远端分支删除不可先于标签验证；`F:\CamelTv` 与其中 `lanhu-mcp` 禁止 reset/clean/checkout。
