---
title: "DEV Batch 32 单一主干迁移看板"
owner: "dev"
last_reviewed: "2026-07-22"
status: "completed"
tags: ["kanban", "git", "worktree"]
---

# DEV Batch 32 — Main Trunk Migration

| Slice | 状态 | 证据/下一步 |
|---|---|---|
| 1 备份 | ✅ | `F:\CamelTv-safe-backup\20260722-201657`，bundle/ZIP/hash 全绿 |
| 2 本地核对 | ✅ | reconciliation 工件；原目录不动 |
| 3 worktree 工具 | ✅ | 自测 PASS |
| 4 Agent/CI/Jenkins | ✅ | 单一 main 规范、隔离工具、CI 门禁与 Jenkins fail-fast 已落地 |
| 5 全量测试/PR | ✅ | 修复后本地后端 654/前端 96；PR #56 六项检查全绿并合入 |
| 6 baseline/rename | ✅ | baseline 标签验证；develop 原地重命名为 main |
| 7 ruleset/legacy | ✅ | main 两项 required checks；旧 master 标签归档后删除 |
| 8 控制 worktree/验收 | ✅ | 控制目录、双 AI、pre-push、递归 clone、1163 指纹均通过；以本收尾 PR 验证 ruleset |

收尾：`F:\CamelTv` 与其中 `lanhu-mcp` 未执行 reset/clean/checkout；今后所有任务从 `origin/main` 使用脚本创建独立 worktree。
