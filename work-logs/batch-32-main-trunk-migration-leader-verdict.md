---
title: "Batch 32 单一主干迁移 Leader 判决"
owner: "leader"
last_reviewed: "2026-07-22"
status: "pending"
tags: ["leader", "git", "migration"]
---

# Batch 32 — Leader Verdict

当前判决：`PENDING`。

只有以下证据同时成立才可改为 APPROVED：

1. 备份可恢复且原运行目录指纹不变。
2. PR #56 本地全量测试与 GitHub required checks 全绿并已通过 PR 合入。
3. `main` 是唯一默认主干，baseline 与 legacy 标签远端可读。
4. `master/develop` 删除前均已满足归档条件。
5. main ruleset、squash-only、自动清理分支和本地 pre-push 均生效。
6. Claude/Codex 双 worktree 创建、隔离、端口元数据和清理实测通过。
7. `lanhu-mcp` 干净递归检出可用，原脏仓库未改变。
