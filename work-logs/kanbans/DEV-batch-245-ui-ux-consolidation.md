# 🗂️ Dev 部门项目看板

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。Dev 每切片完成后更新。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | Batch 245 — UI/UX Consolidation & Task-First Onboarding |
| **关联 PM 计划** | [work-logs/batch-245-ui-ux-consolidation-pm-plan.md](../batch-245-ui-ux-consolidation-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-245-ui-ux-consolidation-prd-summary.md](../batch-245-ui-ux-consolidation-prd-summary.md) |
| **总预估工时** | 8h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-09-14 |
| **最后更新** | 2026-09-14 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | `@/ui` 唯一出口与迁移 | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | 当前切片 |
| 2 | 任务优先首页 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 3 | 登录恢复与可操作性 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | 视觉/a11y/治理验证 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |

---

## 📍 当前位置

```
Batch 245 — @/ui 唯一出口与迁移
├── 已完成: Product/PM/Design 工件、现状审计、worktree 隔离
├── 🔄 进行中: canonical barrel、兼容适配、导入迁移、ESLint 门禁
├── ⏳ 待审批: 切片自测结果
└── ⏳ 下一步: 任务优先首页
```

---

## 📜 批次记录

### Batch 245 — UI/UX Consolidation (2026-09-14)
- **产出**: 待本批完成后记录
- **审批**: 待 QA/Leader/用户总确认
- **耗时**: 进行中

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 批量导入迁移 | P2 | 现有双入口共影响 169 个文件，需机械迁移并全量 typecheck | Dev | 2026-09-14 |
| SMTP 配置 | P2 | 生产是否配置 SMTP 未知；UI 必须显式提示管理员兜底 | QA/运维 | 2026-09-14 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-245-ui-ux-consolidation-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-245-ui-ux-consolidation-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-245-ui-ux-consolidation-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-245-ui-ux-consolidation-qa-report.md) | ⏳ |
| Leader Verdict | [link](../batch-245-ui-ux-consolidation-leader-verdict.md) | ⏳ |
