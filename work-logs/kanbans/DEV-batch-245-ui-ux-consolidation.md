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
| 1 | `@/ui` 唯一出口与迁移 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 164 文件迁移；ESLint + 治理测试 |
| 2 | 任务优先首页 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 4 任务入口 + 可展开模块 |
| 3 | 登录恢复与可操作性 | ✅ | ✅ | ✅ | ⏳ | ⏳ | forgot/reset + 邮件 + Caps Lock |
| 4 | 视觉/a11y/治理验证 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 三视口 6/6 + axe + 截图 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 245 — QA 与 Leader 本地评审完成
├── 已完成: 4 个切片、前后端全量、G0-G2、三视口 axe/截图
├── 🔄 进行中: 等待用户一次总确认（推送 + Draft PR + required checks 后合入）
├── ⏳ 待审批: 用户总确认
└── ⏳ 下一步: 推送 feature/ui-ux-consolidation-phase-3 → Draft PR → checks → squash 合入
```

---

## 📜 批次记录

### Batch 245 — UI/UX Consolidation (2026-09-14)
- **产出**:
  - `ad518a17` Product/PM/Design/看板
  - `69f2a28d` `@/ui` 唯一出口
  - `ba6abc04` 任务优先首页
  - `c013669a` 登录恢复与密码辅助
  - `0354a559` 多视口视觉/axe 证据
  - `782b1533` 工件格式收口
- **审批**: QA PASS（本地）；Leader 有条件通过，等待用户总确认与 CI required checks
- **耗时**: 约 6h
- **记录**: [QA 报告](../batch-245-ui-ux-consolidation-qa-report.md) / [Leader Verdict](../batch-245-ui-ux-consolidation-leader-verdict.md)

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无代码阻塞 | P3 | 邮件投递需生产配置 SMTP 与 FRONTEND_URL；UI 已诚实提示 | 运维/发布负责人 | 2026-09-14 |
| WARN ratchet | P3 | `dev-gate` HARD=0，历史 WARN=330，Phase 4 建基线 | Phase 4 | 2026-09-14 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-245-ui-ux-consolidation-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-245-ui-ux-consolidation-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-245-ui-ux-consolidation-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-245-ui-ux-consolidation-qa-report.md) | ✅ |
| Leader Verdict | [link](../batch-245-ui-ux-consolidation-leader-verdict.md) | ✅ |
