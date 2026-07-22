---
title: "Batch 32 单一主干迁移 QA 报告"
owner: "qa"
last_reviewed: "2026-07-22"
status: "passed"
tags: ["qa", "git", "migration"]
---

# Batch 32 — QA Report

## 已完成证据

| 检查 | 结果 |
|---|---|
| 父仓库 bundle | PASS，完整历史 |
| `lanhu-mcp` bundle | PASS，完整历史 |
| 父仓库脏文件 ZIP | PASS，9 个文件 |
| 蓝湖脏文件 ZIP | PASS，1154 个文件 |
| 备份制品 SHA-256 | PASS，0 mismatch |
| 源文件备份后 SHA-256 | PASS，0 mismatch |
| worktree 工具自测 | PASS：主干拒绝、创建、metadata ignore、重复拒绝、task push、main push block |
| 本地脏内容核对 | PASS：无独有生产逻辑遗漏；危险临时 API 脚本仅备份 |
| `lanhu-mcp` 使用判定 | 必须保留；后端 Provider 直接 import，补 `.gitmodules` |
| 后端 Ruff F821 | PASS |
| 后端应用 import | PASS |
| Alembic 单头 | PASS：`20260722_batch27_merge_missing (batch27)` |
| 迁移 revision 测试 | PASS：1 passed |
| 后端全量 pytest | PASS：654 passed，5 warnings，222.95s（修复后复跑） |
| 前端 clean install | PASS：`npm ci`，897 packages |
| 前端 TypeScript | PASS |
| 前端全量 Vitest | PASS：22 files，96 tests |
| 前端生产构建 | PASS：8.36s |
| OpenVPN 跨平台回归 | PASS：8 tests；显式覆盖 Windows 模拟路径和非 Windows 拒绝路径 |
| PR #56 GitHub 检查 | PASS：6/6，含 Linux 干净检出 654 条后端与 96 条前端 |
| 全新递归 clone | PASS：`lanhu-mcp` 精确检出 `c9f4a43` |
| 已审计基线标签 | PASS：`baseline-2026-07-22-audited` → `09386ff` |
| 旧 master 归档 | PASS：`legacy-master-2026-07-15` → `4298aad` |
| 远端分支 | PASS：默认且唯一永久主干为 `main`；`develop/master` 均不存在 |
| main ruleset | PASS：PR-only、禁止删除/强推、squash-only、2 项 required checks |
| 本地 pre-push | PASS：带新提交的 `HEAD:main --dry-run` 被拒绝，远端未改变 |
| 双 AI worktree | PASS：Claude/Codex 独立分支、目录、端口、env；冲突创建被拒绝 |
| 原运行目录复核 | PASS：1163 个 SHA-256 指纹，0 mismatch；原分支未切换 |

## 最终远端门禁

本文件所在收尾 PR 必须在 `main` ruleset 下通过“后端全新检出与全量回归”和“前端全新检出与全量回归”，并只能 squash 合入。该 PR 同时移除 CI 对已删除 `develop` 的迁移期兼容配置。

补充观察：`npm audit` 报告 17 个既有依赖漏洞（2 critical、7 high、8 moderate），不阻断本次 Git 主干迁移，但必须作为独立安全治理项处理。

远端首轮干净检出发现并阻断 2 个仅在 Linux 暴露的 OpenVPN 测试假设：测试此前默认运行器是 Windows。生产行为保持不变；通过 `_is_windows()` 测试缝显式模拟平台并新增非 Windows 回归用例，第二轮本地 654 条与 GitHub Linux 全量门禁均已确认通过。

当前判决：`PASS`。收尾 PR 全绿并经 ruleset 合入后，迁移闭环成立。
