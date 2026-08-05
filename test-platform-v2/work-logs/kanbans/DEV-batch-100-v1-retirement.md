# 🗂️ Dev 部门项目看板 — Batch 100（V1 整体退役）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | V1 整体退役：web-ui/server/cli 移除 + API 测试资产迁移（完整批次） |
| **关联 PRD** | [batch-100-v1-retirement-prd-summary.md](../batch-100-v1-retirement-prd-summary.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-100-v1-retirement |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 迁移测试资产（generated + specs → tests/） | ✅ | ✅ | ✅ | ✅ | ⏳ | 9 文件迁移 |
| 2 | 更新 CI 路径（workflows + 脚本） | ✅ | ✅ | ✅ | ✅ | ⏳ | |
| 3 | 删除 V1 其余（git rm） | ✅ | ✅ | ✅ | ✅ | ⏳ | 77 文件删除 |
| 4 | 边界与脚本（repo-boundaries/validator） | ✅ | ✅ | ✅ | ✅ | ⏳ | PASS |
| 5 | 文档与技能更新 | ✅ | ✅ | ✅ | ✅ | ⏳ | |
| 6 | C-CONDITIONS（C64-1 关闭） | ✅ | ✅ | ✅ | ✅ | ⏳ | |
| 7 | QA + Leader 工件 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 100 — V1 整体退役（完成）
├── ✅ 迁移：generated + specs → tests/api-testing/（CI 路径同步）
├── ✅ 删除：web-ui/server/cli/core/config/docker 等 77 文件
├── ✅ 边界：deprecated-v1 移除，PASS
├── ✅ C64-1 关闭 + 文档/技能同步
└── 🔄 等一次总确认（push + Draft PR + required checks 后合入）
```
