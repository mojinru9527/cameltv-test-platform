# 🗂️ Dev 部门项目看板 — Batch 70（能力产品化 UI 补齐：C63-1）

> **用途**：追踪 Batch 70 进度节点。Dev 部门启动时必须先读本看板。

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | CamelTv 测试平台 v2 — 能力产品化 UI 补齐 |
| **关联 PM 计划** | [batch-70-capability-ui-pm-plan.md](../batch-70-capability-ui-pm-plan.md) |
| **关联 PRD** | [batch-70-capability-ui-prd-summary.md](../batch-70-capability-ui-prd-summary.md) |
| **总预估工时** | 5h |
| **已用批次** | 70 |
| **看板创建** | 2026-08-03 |
| **最后更新** | 2026-08-03 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | API Token 管理 UI | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置** |
| 2 | 用例导入导出 UI | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 3 | 质量追溯下钻 UI | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | 报告模板管理 UI | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 5 | QA + Leader + PR | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 70 — 能力产品化 UI 补齐
├── 已完成: 六部门前置工件（PRD/PM/Design）；C63-1 对账（Token/导入导出/追溯下钻/模板）
├── 🔄 进行中: Slice 1 API Token 管理 UI
├── ⏳ 待审批: 用户 push 授权（首个 commit 时按 §2.4 展示摘要）
└── ⏳ 下一步: 用例导入导出 UI
```

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| Playground 前端入口 | P2 | C22-C2/C3 runner 链路未验证，本批维持 API-only（文档化） | 后续批次 | 2026-08-03 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PM 计划 | [link](../batch-70-capability-ui-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-70-capability-ui-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-70-capability-ui-qa-report.md) | ⏳ |
| Leader 判决 | [link](../batch-70-capability-ui-leader-verdict.md) | ⏳ |
