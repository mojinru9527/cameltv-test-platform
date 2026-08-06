# 🗂️ Dev 部门项目看板 — Batch 101（体育平台承接）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 体育平台生产环境接入（契约/环境/UI 冒烟/AV/定时/Token） |
| **关联 PRD** | [batch-101-sports-platform-integration-prd-summary.md](../batch-101-sports-platform-integration-prd-summary.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-101-sports-platform-integration |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 接入脚本（契约/环境/UI/AV/定时/Token） | ✅ | ✅ | ✅ | ✅ | ⏳ | |
| 2 | 本地验证（payload 校验） | ✅ | ✅ | ✅ | ✅ | ⏳ | 899 端点+325 用例全流程 |
| 3 | 生产执行 + UI 冒烟触发 | ✅ | ✅ | ✅ | ✅ | ⏳ | 3/5 真实浏览器执行 |
| 4 | 证据/文档/条件 | ✅ | ✅ | ✅ | ✅ | ⏳ | C101-1/2/3 |
| 5 | QA + Leader 工件 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 101 — 体育平台承接（完成）
├── ✅ 生产接入：7 服务 899 端点 + 325 用例 + 计划/环境/UI 任务/Token
├── ✅ UI 冒烟真实浏览器执行 3/5（发现登记 C101-1/2/3）
├── ✅ 凭据恢复（admin 重置 + sportsadmin 新建，用户授权）
└── 🔄 等一次总确认（push + Draft PR + required checks 后合入）
```
