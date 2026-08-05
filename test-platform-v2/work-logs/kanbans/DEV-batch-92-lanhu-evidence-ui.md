# 🗂️ Dev 部门项目看板 — Batch 92（蓝湖证据包审核 UI）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 蓝湖证据包审核 UI 产品化（完整批次） |
| **关联 PRD** | [batch-92-lanhu-evidence-ui-prd-summary.md](../batch-92-lanhu-evidence-ui-prd-summary.md) |
| **看板创建** | 2026-08-05 |
| **执行器** | codex（用户确认 2026-08-05） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-92-lanhu-evidence-ui（frontend 5219 / backend 8049） |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 后端 seed 菜单 | ✅ | ✅ | ✅ | ✅ | ⏳ | menu 下发 |
| 2 | 状态标签纯函数（TDD） | ✅ | ✅ | ✅ | ✅ | ⏳ | vitest 4/4 |
| 3 | 任务列表页 | ✅ | ✅ | ✅ | ✅ | ⏳ | 冒烟截图 |
| 4 | 任务详情页（审核/导入） | ✅ | ✅ | ✅ | ✅ | ⏳ | typecheck |
| 5 | 路由 + QA 门禁 + 证据 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 92 — 蓝湖证据包审核 UI（完成）
├── ✅ /lanhu-evidence 列表 + 新建
├── ✅ /lanhu-evidence/:id 详情 + 审核 + 导入
├── ✅ seed 菜单 + 权限四档门控
├── ✅ 门禁全绿（vitest 338 / pytest 1054 / 冒烟 1/1）
└── 🔄 等一次总确认
```

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [batch-92-lanhu-evidence-ui-prd-summary.md](../batch-92-lanhu-evidence-ui-prd-summary.md) | ✅ |
| PM 计划 | [batch-92-lanhu-evidence-ui-pm-plan.md](../batch-92-lanhu-evidence-ui-pm-plan.md) | ✅ |
| Design | [batch-92-lanhu-evidence-ui-design-spec.md](../batch-92-lanhu-evidence-ui-design-spec.md) | ✅ |
