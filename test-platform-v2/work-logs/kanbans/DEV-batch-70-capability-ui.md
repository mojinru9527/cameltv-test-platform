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
| **最后更新** | 2026-08-03（Slice 1~4 完成，QA/Leader 已出） |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | API Token 管理 UI | ✅ | ✅ | ✅ | ⏳ | ⏳ | E2E：创建/明文展示/落库 |
| 2 | 用例导入导出 UI | ✅ | ✅ | ✅ | ⏳ | ⏳ | E2E：导入 50 条/导出 xlsx |
| 3 | 质量追溯下钻 UI | ✅ | ✅ | ✅ | ⏳ | ⏳ | E2E：需求→用例→执行/缺陷 |
| 4 | 报告模板管理 UI | ✅ | ✅ | ✅ | ⏳ | ⏳ | E2E：新建模板入列表 |
| 5 | QA + Leader + PR | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | ⏳ | **当前位置** |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 70 — 能力产品化 UI 补齐
├── 已完成: Slice 1~4 全部实现并验证（Token/导入导出/追溯下钻/模板管理）；Playground 维持 API-only（文档化）
├── ✅ QA PASS（45/45 + 四 Slice E2E）+ Leader APPROVED
├── 🔄 进行中: Slice 5 PR 交付
├── ⏳ 待审批: 用户 push 授权（Slice 2~4 + QA/Leader commit，按 §2.4 展示摘要）
└── ⏳ 下一步: Draft PR → checks → 二次确认 → 合入
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
