---
title: "Batch 32 单一主干迁移 QA 报告"
owner: "qa"
last_reviewed: "2026-07-22"
status: "in_progress"
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
| 后端全量 pytest | PASS：653 passed，5 warnings，229.01s |
| 前端 clean install | PASS：`npm ci`，897 packages |
| 前端 TypeScript | PASS |
| 前端全量 Vitest | PASS：22 files，96 tests |
| 前端生产构建 | PASS：8.36s |
| OpenVPN 跨平台回归 | PASS：8 tests；显式覆盖 Windows 模拟路径和非 Windows 拒绝路径 |

## 待完成门禁

- 子模块全新递归检出。
- PR #56 远端全量检查。
- baseline/legacy 标签、分支重命名/删除、ruleset 和 merge policy。
- 双 AI 真实 worktree 隔离及原运行目录指纹复核。

补充观察：`npm audit` 报告 17 个既有依赖漏洞（2 critical、7 high、8 moderate），不阻断本次 Git 主干迁移，但必须作为独立安全治理项处理。

远端首轮干净检出发现并阻断 2 个仅在 Linux 暴露的 OpenVPN 测试假设：测试此前默认运行器是 Windows。生产行为保持不变；通过 `_is_windows()` 测试缝显式模拟平台并新增非 Windows 回归用例，待第二轮远端门禁确认。

当前判决：`LOCAL PASS / REMOTE IN PROGRESS`，禁止提前删除远端分支。
