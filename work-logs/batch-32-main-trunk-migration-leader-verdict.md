---
title: "Batch 32 单一主干迁移 Leader 判决"
owner: "leader"
last_reviewed: "2026-07-22"
status: "approved"
tags: ["leader", "git", "migration"]
---

# Batch 32 — Leader Verdict

当前判决：`APPROVED`，生效条件是本文件所在收尾 PR 通过 `main` 的两项 required checks 并以 squash 合入。

以下证据已成立：

1. 备份可恢复且原运行目录指纹不变。
2. PR #56 本地全量测试与 GitHub required checks 全绿并已通过 PR 合入。
3. `main` 是唯一默认主干，baseline 与 legacy 标签远端可读。
4. `master/develop` 删除前均已满足归档条件。
5. main ruleset、squash-only、自动清理分支和本地 pre-push 均生效。
6. Claude/Codex 双 worktree 创建、隔离、端口元数据和清理实测通过。
7. `lanhu-mcp` 干净递归检出可用，原脏仓库未改变。

## 最终证据

- PR #56：6/6 检查通过，squash 合入 `09386ff`。
- 远端：默认分支 `main`，无 `develop/master`；两枚归档标签均反查到精确提交。
- 规则：禁止主干直接写入、删除和强推；仅 squash；两项干净检出全量检查必需。
- 本地：控制 worktree 干净跟踪 `origin/main`；Claude/Codex 隔离、端口冲突和 pre-push 实测通过。
- 安全：原 `F:\CamelTv` 1163 个源文件指纹 0 mismatch，原分支和脏内容保持不变。

剩余事项不是本批次阻断项：运营后台生产验收仍需只读地址/账号；17 个 npm 依赖告警需独立安全批次处理。
