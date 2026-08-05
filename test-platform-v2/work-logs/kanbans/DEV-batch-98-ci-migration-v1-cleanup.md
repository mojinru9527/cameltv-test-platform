# 🗂️ Dev 部门项目看板 — Batch 98（CI 迁移 + V1 工具删除）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | CI 迁移（V1 CLI → 脚本/Playwright）+ 11 工具删除 + C64-3/C96-1 关闭（完整批次） |
| **关联 PRD** | [batch-98-ci-migration-v1-cleanup-prd-summary.md](../batch-98-ci-migration-v1-cleanup-prd-summary.md) |
| **看板创建** | 2026-08-05 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-98-ci-migration-v1-cleanup |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | CI 回归脚本（health/run/collect-elk） | ✅ | ✅ | ✅ | ✅ | ⏳ | 三子命令本地实测 |
| 2 | api-regression.yml 迁移 | ✅ | ✅ | ✅ | ✅ | ⏳ | 无 tp 引用 |
| 3 | prod-smoke.yml 迁移（去空跑） | ✅ | ✅ | ✅ | ✅ | ⏳ | 6 只读 spec |
| 4 | 删除 11 个 V1 工具 | ✅ | ✅ | ✅ | ✅ | ⏳ | 21 文件删除 |
| 5 | cli/server 引用清理 | ✅ | ✅ | ✅ | ✅ | ⏳ | rg 0 命中 |
| 6 | 元数据与文档（boundary/C 条件/交付清单） | ✅ | ✅ | ✅ | ✅ | ⏳ | C64-3 关闭 |
| 7 | QA + Leader 工件 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 98 — CI 迁移 + V1 工具删除（完成）
├── ✅ scripts/ci/api-regression.ps1（health/run/collect-elk 实测）
├── ✅ api-regression.yml + prod-smoke-test.yml 迁移（tp 0 引用，prod smoke 去空跑）
├── ✅ 11 个 V1 工具删除 + cli/server 引用清理（rg 0 命中）
├── ✅ C64-3 关闭 + C96-1 部分关闭 + 文档同步
└── 🔄 等一次总确认（push + Draft PR + required checks 全绿后合入）
```
